# -*- coding: utf-8 -*-
"""
    Yewdocs
    ~~~~~~~

    Yewdocs is a personal document manager that makes creating and
editing text documents from the command line easier than using an
editor and filesystem commands.

    :copyright: (c) 2017 by Paul Wolf.
    :license: BSD, see LICENSE for more details.

"""
from typing import Dict, Optional
import codecs
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import traceback
import uuid
from collections import namedtuple
from os.path import expanduser
import json

import glom
import click
import dateutil
import dateutil.parser
import humanize as h
import markdown
import pytz
import requests
import tzlocal
from jinja2 import Template
from requests.exceptions import ConnectionError
from strgen import StringGenerator as SG

from .crypt import decrypt_file, encrypt_file, list_keys
from .remote import OfflineException, Remote, RemoteException
from .store import YewStore
from .document import Document
from .document import DOC_KINDS
from .settings import USER_PREFERENCES
from .settings import Preferences
from . import settings
from . import file_system as fs
from .tag import Tag, TagDoc
from .utils import (
    bcolors,
    delete_directory,
    err,
    get_sha_digest,
    get_short_uid,
    is_binary_file,
    is_binary_string,
    is_short_uuid,
    is_uuid,
    modification_date,
    slugify,
    to_utc,
)

__version__ = "0.2.0"
__author__ = "Paul Wolf"
__license__ = "BSD"

try:
    import pypandoc
except Exception:
    print("pypandoc won't load; convert cmd will not work")

# suppress pesky warnings while testing locally
requests.packages.urllib3.disable_warnings()


class YewCLI(object):
    """Wraps two principle classes.

    We manage the store and remote objects.

    """

    def __init__(self, username=None):
        self.store = YewStore(username=username)
        self.remote = Remote(self.store)


@click.group()
@click.option("--user", help="User name", required=False)
def cli(user):
    global yew
    yew = YewCLI(username=user)


@cli.command()
def status():
    """Print info about current setup."""
    click.echo("Version  : %s" % __version__)
    click.echo("User     : %s" % yew.store.username)
    click.echo("Storage  : %s" % yew.store.yew_dir)
    click.echo("Offline  : %s" % yew.store.offline)


@cli.command()
@click.argument("name", required=False)
@click.option(
    "--kind",
    "-k",
    default="md",
    help="Type of document, txt, md, rst, json, etc.",
    required=False,
)
def create(name, kind):
    """Create a new document."""
    if not name:
        docs = yew.store.search_names("%s")
        for index, doc in enumerate(docs):
            click.echo("%s [%s]" % (doc.name, doc.kind))

        sys.exit(0)

    # get the type of file
    kind_tmp = yew.store.prefs.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp

    doc = yew.store.create_document(name, kind)

    click.echo("created document: %s" % doc.uid)
    click.edit(require_save=True, filename=doc.path)
    yew.remote.push_doc(yew.store.get_doc(doc.uid))


@cli.command()
@click.argument("tagname", required=False)
@click.argument("docname", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--create", "-c", is_flag=True, required=False)
@click.option(
    "--untag",
    "-u",
    is_flag=True,
    required=False,
    help="Remove a tag association from document(s)",
)
def tag(tagname, docname, list_docs, create, untag):
    """Manage tags.

    Use this command to create tags, associate them with documents and
    remove tags.

    The tag command with no further arguments or options will list all tags.

    """

    tag = None
    if tagname:
        tagname = tagname.lower()
    if tagname and create:
        tag = yew.store.get_or_create_tag(tagname)
        click.echo("created: %s %s" % (tag.tagid, tag.name))
    elif create and not tagname:
        click.echo("tag name required")
    elif tagname and docname:
        if not tag:
            tags = yew.store.get_tags(tagname, exact=True)
        if len(tags) > 0:
            tag = tags[0]
        if not tag:
            click.echo("No tags found")
            sys.exit(0)
        docs = get_document_selection(docname, list_docs, multiple=True)
        if docs and isinstance(docs, list):
            for doc in docs:
                if untag:
                    yew.store.dissociate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s removed" % (tag.name, doc.name))
                else:
                    yew.store.associate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s" % (tag.name, doc.name))
        elif docs:
            doc = docs
            if untag:
                yew.store.dissociate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s removed" % (tag.name, doc.name))
            else:
                yew.store.associate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s" % (tag.name, doc.name))
    else:
        # list tags
        tags = yew.store.get_tags(tagname)
        for tag in tags:
            click.echo(tag.name)


@cli.command()
@click.option("--tag", "-t", required=False, help="Set a tag as a filter.")
@click.option("--clear", "-c", is_flag=True, required=False, help="Clear the context.")
def context(tag, clear):
    """Set or unset a tag context filter for listings.

    A context is essentially a filter. When a context, like a tag is
    set, operations that list documents will filter the
    documents. Like the `ls` command with a context of `-t foo` will
    only list documents tagged with `foo`.

    Use `--clear` to clear the context.

    Currently, only a single tag is allowed for context.

    """
    tags = None
    current_tag_context = yew.store.prefs.get_user_pref("tag_context")
    if tag:
        # lookup tag
        tags = yew.store.get_tags(tag, exact=True)
        if not tags:
            click.echo("Tag not found; must be exact match")
            sys.exit(1)
        elif len(tags) > 1:
            click.echo(
                "More than one tag found. Only one tag allowed. Tags matching: %s"
                % ", ".join(tags)
            )
            sys.exit(1)
        yew.store.put_user_pref("tag_context", tags[0].tagid)
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")

    if clear:
        yew.store.prefs.delete_user_pref("tag_context")
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")

    if current_tag_context:
        click.echo("current tag context: %s" % yew.store.get_tag(current_tag_context))


@cli.command()
@click.argument("name", required=False)
@click.argument("value", required=False)
def user_pref(name, value):
    """Show or set user preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    print("user-pref, name={}, value={}".format(name, value))

    if name and not value:
        click.echo("%s = %s" % (name, prefs.get_user_pref(name)))
    elif name and value:
        yew.store.prefs.put_user_pref(name, value)
    else:
        for k in settings.user_preferences:
            v = yew.store.prefs.get_user_pref(k)
            click.echo("%s = %s" % (k, v))


def parse_ranges(s):
    """Parse s as a list of range specs."""
    range_list = []  # return value is a list of doc indexes
    ranges = s.split(",")
    # list of ranges
    for r in ranges:
        try:
            i = int(r)
            range_list.append(i)
        except ValueError:
            # check if range
            if "-" in r:
                start, end = r.split("-")
                start = int(start)
                end = int(end)
                range_list.extend([x for x in range(start, end + 1)])
    return range_list


def document_menu(docs, multiple=False):
    """Show list of docs. Return selection."""
    if not len(docs):
        return None
    for index, doc in enumerate(docs):
        click.echo("%s) %s" % (index, doc.name))
    if multiple:
        v = click.prompt("Select document")
        index_list = parse_ranges(v)
        doc_list = []
        for i in index_list:
            if i in range(len(docs)):
                doc_list.append(docs[i])
        return doc_list  # returning a list of docs!!
    else:
        v = click.prompt("Select document", type=int)
        if v not in range(len(docs)):
            print("Choice not in range")
            sys.exit(1)
    return docs[v]


def get_document_selection(name, list_docs, multiple=False):
    """Present lists or whatever to get doc choice.

    name (str): a title or partial title to use as search
    list_docs (bool): a flag to list documents are not.
    ranges (bool): allow range of integers for a list selection?

    If there is no name, show recent list.
    otherwise, show all docs

    We let user specify if a list of docs should be returned.
    In that case, the return value's type is a list.

    """

    if name and is_uuid(name):
        return yew.store.get_doc(name)

    if name and is_short_uuid(name):
        return yew.store.get_short(name)

    if not name and not list_docs:
        docs = yew.store.get_recent(yew.store.username)
        return document_menu(docs, multiple)
    elif list_docs:
        docs = yew.store.get_docs()
        if len(docs) == 1:
            return docs[0]
        return document_menu(docs, multiple)
    elif name:
        docs = yew.store.search_names(name)
        if len(docs) == 1:
            return docs[0]
        return document_menu(docs, multiple)

    return None


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--open-file",
    "-o",
    is_flag=True,
    required=False,
    help="Open the file in your host operating system.",
)
@click.option(
    "--gpghome",
    "-g",
    required=False,
    default=".gnupg",
    help="Your GnuGPG home directory, defaults to .gnupg",
)
def edit(name, list_docs, open_file, gpghome):
    """Edit a document.

    Set your $EDITOR environment variable to determine what editor
    will handle the file.

    When the editor is closed, the file will sync to the server
    if you are registered with a Yewdoc cloud instance
    (and if not working offline).

    --open-file will send the document to the host operating system
    for it to decide how to open the file. Since using this option
    means the editor is not a child process, you need to manually sync
    with remote to push changes.

    """

    doc = get_document_selection(name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not doc:
        if click.confirm("Couldn't find that document, shall we create it?"):
            doc = yew.store.create_document(name, kind="md")
        else:
            sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")

    encrypted = doc.check_encrypted()
    if encrypted:
        decrypt_file(doc.get_path(), email, gpghome)
    if open_file:
        # send to host os to ask it how to open file
        click.launch(doc.get_path())
    else:
        click.edit(editor="emacs", require_save=True, filename=doc.path)

    if encrypted:
        encrypt_file(doc.get_path(), email, gpghome)

    yew.remote.push_doc(yew.store.get_doc(doc.uid))
    # yew.store.prefs.put_user_pref("current_doc", doc.uid)
    # yew.store.prefs.update_recent(doc)


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--gpghome",
    "-g",
    required=False,
    default=".gnupg",
    help="Your GnuGPG home directory, defaults to .gnupg",
)
def encrypt(name, list_docs, gpghome):
    """Encrypt a document."""

    doc = get_document_selection(name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not doc:
        sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")

    # try to encrypt in place
    encrypt_file(doc.get_path(), email, gpghome)

    yew.remote.push_doc(yew.store.get_doc(doc.uid))
    yew.store.prefs.put_user_pref("current_doc", doc.uid)
    yew.store.update_recent("yewser", doc)


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--gpghome",
    "-g",
    required=False,
    default=".gnupg",
    help="Your GnuGPG home directory, defaults to ",
)
def decrypt(name, list_docs, gpghome):
    """Decrypt a document."""

    doc = get_document_selection(name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not doc:
        sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")

    # try to decrypt in place
    decrypt_file(doc.get_path(), email, gpghome)

    yew.remote.push_doc(yew.store.get_doc(doc.uid))
    yew.store.prefs.put_user_pref("current_doc", doc.uid)
    yew.store.update_recent("yewser", doc)


@cli.command()
@click.argument("spec", required=True)
@click.option("--string-only", "-s", is_flag=True, required=False)
@click.option("--insensitive", "-i", is_flag=True, required=False)
# @click.option('--remote','-r',is_flag=True, required=False)
def find(spec, string_only, insensitive):
    """Search for spec in contents of docs.

    spec is a regular expression unless string-only is selected
    in which case a simple string match is used.

    """

    docs = yew.store.get_docs()

    for doc in docs:
        found = False
        if string_only:
            if not insensitive:
                if spec in doc.get_content():
                    found = True
            else:
                if spec.lower() in doc.get_content().lower():
                    found = True
        elif re.search(spec, doc.get_content()):
            found = True

        if found:
            click.echo(doc.name)


@cli.command()
@click.argument("name", required=False)
@click.option("--info", "-l", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
@click.option("--humanize", "-h", is_flag=True, required=False)
@click.option("--encrypted", "-e", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.option("--sort", "-s", required=False)
def ls(name, info, remote, humanize, encrypted, tags, sort):
    """List documents."""

    if remote:
        response = yew.remote.get_docs()
        for doc in response:
            click.echo("%s %s" % (get_short_uid(doc["uid"]), doc["title"]))

        sys.exit(0)
    tag_objects = []
    if tags:
        tag_objects = yew.store.parse_tags(tags)
    else:
        # check for context
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")
        if current_tag_context:
            tag_objects = [yew.store.get_tag(current_tag_context)]
            click.echo("Current tag context: %s" % str(tag_objects[0]))
    if name:
        docs = yew.store.search_names(name, encrypted=encrypted)
    else:
        docs = yew.store.get_docs(tag_objects=tag_objects, encrypted=encrypted)

    # for doc in docs:
    #     if not os.path.exists(doc.path):
    #         continue
    #     basename = doc.name.replace(os.sep, "-")
    #     new_path = os.path.join(doc.directory_path, f"{basename}.{doc.kind}")
    #     os.rename(
    #         doc.path,
    #         new_path
    #     )
    #     print(f"Renamed: {new_path}")
    #     # raise SystemExit
    # return

    if sort:
        pass
    else:
        docs.sort(key=lambda doc: doc.updated, reverse=True)

    data = []
    for doc in docs:
        # data.append(doc.serialize(no_content=True))
        if info:
            if doc.is_link():
                click.echo("ln ", nl=False)
            else:
                click.echo("   ", nl=False)
            click.echo(doc.short_uid(), nl=False)
            click.echo("   ", nl=False)
            click.echo(doc.kind.rjust(5), nl=False)
            click.echo("   ", nl=False)
            if not os.path.exists(doc.path):
                click.echo("File does not exist")
                continue
            
            if humanize:
                click.echo(h.naturalsize(doc.get_size()).rjust(10), nl=False)
            else:
                click.echo(str(doc.get_size()).rjust(10), nl=False)
            click.echo("   ", nl=False)
            if humanize:
                click.echo(
                    h.naturaltime(
                        doc.get_last_updated_utc().replace(tzinfo=None)
                    ).rjust(15),
                    nl=False,
                )
            else:
                click.echo(
                    doc.get_last_updated_utc()
                    .replace(microsecond=0)
                    .replace(tzinfo=None),
                    nl=False,
                )
            if doc.is_encrypted():
                click.echo(" (E)", nl=False)
            else:
                click.echo("    ", nl=False)

        # path = os.path.join(fs.get_user_directory(), "index.json")
        # with open(path, "w") as f:
        #     f.write(json.dumps(data, indent=4))

        click.echo(doc.name, nl=False)
        if info:
            click.echo("   ", nl=False)
            # click.echo(slugify(doc.name), nl=False)
        click.echo("")


def pdoc(doc, status, verbose):
    """Print status to stdout."""

    if status == Remote.STATUS_REMOTE_SAME and not verbose:
        print(".", end="", flush=True)
    else:
        click.echo("", nl=True)
        click.echo(doc.name, nl=False)
        msg = Remote.STATUS_MSG[status]
        click.echo(": ", nl=False)
        click.secho(msg, fg="yellow")


@cli.command()
@click.argument("name", required=False)
@click.option(
    "--force", "-f", is_flag=True, required=False, help="Don't confirm deletes"
)
@click.option(
    "--prune",
    "-p",
    is_flag=True,
    required=False,
    help="Delete local docs marked as deleted on server",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    required=False,
    help="Print document status even when no change",
)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def sync(name, force, prune, verbose, list_docs):
    """Pushes local docs and pulls docs from remote.

    We don't overwrite newer docs.
    Does nothing if docs are the same.

    """
    v = verbose
    # make sure we are online
    try:
        r = yew.remote.ping()
    except OfflineException:
        click.echo("can't sync in offline mode")

    if name:
        doc = get_document_selection(name, list_docs)
        docs_local = [doc]
    else:
        docs_local = yew.store.get_docs()
    remote_done = []

    for doc in docs_local:
        try:
            c = yew.remote.doc_status(doc.uid)
            if c == Remote.STATUS_REMOTE_SAME:
                pdoc(doc, c, v)
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_NEWER:
                # click.echo("get newer content from remote: %s %s" % (doc.short_uid(), doc.name))

                remote_doc = yew.remote.fetch(doc.uid)
                # a dict
                doc.put_content(remote_doc["content"])
                if not remote_doc["title"] == doc.name:
                    yew.store.rename_doc(doc, remote_doc["title"])
                #  click.secho("got remote", fg='green')
                pdoc(doc, c, v)
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_OLDER:
                # click.echo("push newer content to remote : %s %s" % (doc.short_uid(), doc.name))
                status_code = yew.remote.push_doc(doc)
                if status_code == 200:
                    pdoc(doc, c, v)
                    #  click.secho('pushed successfully', fg='green')
                else:
                    click.secho(
                        "push failed: {}, {}".format(doc, status_code), fg="red"
                    )

                remote_done.append(doc.uid)
            elif c == Remote.STATUS_DOES_NOT_EXIST:
                #  click.echo("push new doc to remote       : %s %s" % (doc.short_uid(), doc.name))
                print(yew.remote.push_doc(doc))
                if r.status_code == 200:
                    #  click.secho('pushed successfully', fg='green')
                    pdoc(doc, c, v)
                else:
                    click.secho("pushed failed", fg="red")
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_DELETED:
                # click.echo("remote was deleted           : %s %s" % (doc.short_uid(), doc.name))
                if prune:
                    yew.store.delete_document(doc)
                    #  click.secho("pruned local", fg='green')
                    pdoc(doc, c, v)
                else:
                    pdoc(doc, c, v)
            else:
                raise Exception("Invalid remote status   : %s for %s" % (c, str(doc)))
        except Exception as e:
            print(f"An error occured trying to sync {doc}")
            print(e)
    print("")

    # if we chose to update a single doc, we are done, no tag updates or anything else
    # because remote_done won't have values for the follow step to make sense
    if name:
        return

    remote_docs = yew.remote.get_docs()
    for rdoc in remote_docs:
        if rdoc["uid"] in remote_done:
            continue
        remote_doc = yew.remote.fetch(rdoc["uid"])
        click.echo(
            "importing doc: %s %s"
            % (remote_doc["uid"].split("-")[0], remote_doc["title"])
        )
        yew.store.import_document(
            remote_doc["uid"],
            remote_doc["title"],
            remote_doc["kind"],
            remote_doc["content"],
        )

    if False:
        r = yew.remote.push_tag_associations()
        if not r.status_code == 200:
            click.secho(r.text, fg="red")
        tags = yew.store.get_tags("")
        if len(tags) > 0:
            click.echo("syncing tags to server")
            tag_data = {}
            for tag in tags:
                tag_data[tag.tagid] = tag.name

            yew.remote.push_tags(tag_data)

        # get tags from server
        tags = yew.remote.pull_tags()
        if tags:
            click.echo("syncing tags from server")
            for tagid, name in tags.items():
                yew.store.sync_tag(tagid, name)

        tag_docs = yew.remote.pull_tag_associations()
        if tag_docs:
            click.echo("syncing tag associations")
            for tag_association in tag_docs:
                tid = tag_association["tid"]
                uid = tag_association["uid"]
                yew.store.associate_tag(uid, tid)


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
def delete(name, list_docs, force, remote):
    """Delete a document.

    To delete a remote document, it needs to be local. So,
    you may need to sync it from remote before deleting it.

    """

    docs = get_document_selection(name, list_docs, multiple=True)
    if not docs:
        click.echo("no matching documents")
        return
    if not isinstance(docs, list):
        docs = [docs]
    for doc in docs:
        click.echo("Document: %s  %s" % (doc.uid, doc.name))
    d = True
    if not force:
        d = click.confirm("Do you want to continue to delete the document(s)?")
    if d:
        for doc in docs:
            yew.store.delete_document(doc)
            if remote:
                yew.remote.delete("document/%s" % doc.uid)
                click.echo("removed %s" % doc.name)


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
def show(name, list_docs, remote):
    """Send contents of document to stdout."""

    doc = get_document_selection(name, list_docs)
    if remote:
        remote_doc = yew.remote.fetch(doc.uid)
        if remote_doc:
            click.echo(remote_doc["content"])
    else:
        if doc:
            click.echo(doc.get_content())
        else:
            click.echo("no matching documents")
    sys.stdout.flush()


def diff_content(doc1, doc2):
    # d = difflib.Differ()
    # diff = d.compare(doc1,doc2)
    diff = difflib.ndiff(doc1, doc2)
    click.echo("\n".join(list(diff)))


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
@click.option("--diff", "-d", is_flag=True, required=False)
def describe(name, list_docs, remote, diff):
    """Show document details."""

    doc = get_document_selection(name, list_docs)

    if doc:
        doc.dump()
    status = None
    if remote:
        r_info = yew.remote.doc_exists(doc.uid)
        click.echo("Remote: ")
        for k, v in r_info.items():
            click.echo("%s: %s" % (k, v))
        status = yew.remote.doc_status(doc.uid)
        click.echo(Remote.STATUS_MSG[status])
    if (
        doc
        and diff
        and not status == Remote.STATUS_REMOTE_SAME
        and not Remote.STATUS_NO_CONNECTION
    ):
        remote_doc = yew.remote.fetch(doc.uid)
        s = diff_content(
            remote_doc["content"].rstrip().splitlines(),
            doc.get_content().rstrip().splitlines(),
        )
        click.echo(s)


@cli.command()
@click.option("--prune", "-p", is_flag=True, required=False)
def verify(prune=False):
    """Check docs exist."""

    missing = yew.store.verify_docs(prune=prune)
    if prune and missing:
        print("Removed missing")
    if not missing:
        print("No missing docs")


@cli.command()
@click.argument("name1", required=True)
@click.argument("name2", required=True)
def diff(name1, name2):
    """Compare two documents."""

    doc1 = get_document_selection(name1, list_docs=False)
    doc2 = get_document_selection(name2, list_docs=False)
    """Compare two documents."""

    s = diff_content(
        doc1.get_content().rstrip().splitlines(),
        doc2.get_content().rstrip().splitlines(),
    )
    click.echo(s)


@cli.command()
def push():
    """Push all documents to the server."""
    if yew.remote.offline:
        pass
    docs = yew.store.get_docs()
    result = ""
    for doc in docs:
        click.echo("pushing: %s:" % doc.name, nl=False)
        status = yew.remote.push_doc(doc)
        if status == Remote.STATUS_REMOTE_SAME:
            result = " No difference"
        elif status == Remote.STATUS_REMOTE_NEWER:
            result = " can't push because remote newer"
        elif status == Remote.STATUS_REMOTE_OLDER:
            result = " local newer, pushed"
        elif status == Remote.STATUS_DOES_NOT_EXIST:
            result = " no remote version, creating"
        click.echo(result)
    click.echo("Done!")


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def head(name, list_docs):
    """Send start of document to stdout."""

    doc = get_document_selection(name, list_docs)
    click.echo(doc.get_content()[:250])


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def tail(name, list_docs):
    """Send end of document to stdout."""

    doc = get_document_selection(name, list_docs)
    click.echo(doc.get_content()[-250:])


@cli.command()
@click.argument("name", required=False)
@click.argument("new_name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def rename(name, new_name, list_docs):
    """Rename a document."""

    doc = get_document_selection(name, list_docs)
    if not new_name:
        click.echo("Rename: '%s'" % doc.name)
        new_name = click.prompt("Enter the new document title ", type=str)
    if new_name:
        doc = yew.store.rename_doc(doc, new_name)
    yew.remote.push_doc(doc)


@cli.command()
@click.argument("name", required=False)
@click.argument("kind", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def kind(name, kind, list_docs):
    """Change kind of document."""

    doc = get_document_selection(name, list_docs)
    if not kind:
        click.echo(doc)
        click.echo("Current document kind: '%s'" % doc.kind)
        for i, d in enumerate(DOC_KINDS):
            click.echo("%s" % (d))
        kind = click.prompt("Select the new document kind ", type=str)
    click.echo("Changing document kind to: %s" % kind)
    doc = yew.store.change_doc_kind(doc, kind)
    try:
        yew.remote.push_doc(doc)
    except Exception as e:
        print(e)
    sys.exit(0)


@cli.command()
def ping():
    """Ping server."""
    r = yew.remote.ping()
    if r is None:
        print("No response")
        sys.exit(1)
    if r.status_code == 200:
        print(r.content)
        sdt = dateutil.parser.parse(r.json())
        click.echo("Server time  : %s" % sdt)
        click.echo("Here time    : {}".format(datetime.datetime.now()))
        n = datetime.datetime.now()
        if n > sdt:
            d = n - sdt
        else:
            d = sdt - n
        click.echo("Skew         : %s" % str(d))
        sys.exit(0)
    click.echo("ERROR HTTP code={}, msg={}".format(r.status_code, r.content))


@cli.command()
def api():
    """Get API of the server."""
    r = yew.remote.api()
    if not r:
        sys.exit(1)
    if r.status_code == 200:
        # content should be server time
        s = json.dumps(r.json(), sort_keys=True, indent=4, separators=(",", ": "))
        click.echo(s)
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)


@cli.command()
@click.argument("name", required=False)
@click.argument("template", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
def browse(name, template, list_docs, tags):
    """Convert to html and attempt to load in web browser.

    Provide a name spec or tags to select documents.

    You can provide your own Jinja (http://jinja.pocoo.org/)
    template. Leave this out to use the default.

    """

    if template:
        template_path = template
    else:
        # get our default
        p = os.path.realpath(__file__)
        template_path = os.path.dirname(p)
        template_path = os.path.join(template_path, "template_0.html")
    if not os.path.exists(template_path):
        click.echo("does not exist: {}".format(template_path))
        sys.exit(1)

    input_formats = ["md", "rst"]

    tag_objects = yew.store.parse_tags(tags) if tags else None
    if name:
        docs = yew.store.search_names(name)
    else:
        docs = yew.store.get_docs(tag_objects=tag_objects)

    nav = ""
    for doc in docs:
        tmp_dir = yew.store.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        a = '<a href="file://%s">%s</a><br/>\n' % (tmp_file, doc.name)
        nav += a
    for doc in docs:
        if doc.kind == "md":
            #  html = markdown.markdown(doc.get_content())
            pdoc_args = ["--mathjax"]

            html = pypandoc.convert(
                doc.get_path(), format="md", to="html5", extra_args=pdoc_args
            )

        else:
            if doc.kind not in input_formats:
                kind = "md"
            else:
                kind = doc.kind
            html = pypandoc.convert(doc.get_path(), format=kind, to="html")
        tmp_dir = yew.store.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        with click.open_file(template_path, "r") as f:
            t = f.read()

        template = Template(t)
        data = {"title": doc.name, "content": html, "nav": nav}
        dest = template.render(data)

        # template = string.Template(t)
        # dest = template.substitute(
        #     title=doc.name,
        #     content=html,
        #     nav=nav
        # )
        f = codecs.open(tmp_file, "w", "utf-8").write(dest)

    click.launch(tmp_file)


@cli.command()
@click.argument("name", required=False)
@click.argument("destination_format", required=False)
@click.argument("destination_file", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--formats", "-f", is_flag=True, required=False)
def convert(name, destination_format, destination_file, list_docs, formats):
    """Convert to destination_format and print to stdout or save to file if provided."""

    if formats or not destination_format:
        formats = pypandoc.get_pandoc_formats()
        click.echo("Input formats:")
        for f in formats[0]:
            click.echo("\t" + f)
        click.echo("Output formats:")
        for f in formats[1]:
            click.echo("\t" + f)
        sys.exit(0)

    doc = get_document_selection(name, list_docs)
    click.echo(doc.name)
    click.echo(doc.kind)
    click.echo(destination_format)

    if destination_format in ["docx", "pdf", "odt"]:
        destination_file = "{}.{}".format(slugify(doc.name), destination_format)

    if destination_file:
        dest = pypandoc.convert(
            doc.get_content(),
            format=doc.kind,
            to=destination_format,
            outputfile=destination_file,
        )
        click.echo(destination_file)
    else:
        dest = pypandoc.convert_text(
            doc.get_content(), format=doc.kind, to=destination_format
        )
        click.echo(dest)
    sys.stdout.flush()


@cli.command()
@click.argument("path", required=True)
@click.option("--kind", "-k", required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.option("--symlink", "-s", is_flag=True, required=False)
def take(path, kind, force, symlink):
    """Import a file as a document.

    The base filename becomes the document title.

    Should be a text type, but we leave that to user.

    --force will cause a similarly titled document to be overwritten
    in the case of a name conflict.

    """
    if not os.path.exists(path) or not os.path.isfile(path):
        click.echo("path does not exist: %s" % path)
        sys.exit(1)

    content = None

    # slurp file
    if not symlink:
        with click.open_file(path, "r", "utf-8") as f:
            content = f.read()

    # get location, filename, etc.
    fn = os.path.basename(path)
    filename, file_extension = os.path.splitext(fn)
    if not kind:
        kind = "txt"
    title = os.path.splitext(path)[0]

    # check if we have one with this title
    # the behaviour we want is for the user to continuously
    # ingest the same file that might be updated out-of-band
    # TODO: handle multiple titles of same name
    docs = yew.store.search_names(title, exact=True)
    if docs and not symlink:
        if len(docs) >= 1:
            if not force:
                click.echo("A document with this title exists already")
            if force or click.confirm(
                "Overwrite existing document: %s ?" % docs[0].name, abort=True
            ):
                docs[0].put_content(content)
                yew.remote.push_doc(docs[0])
                sys.exit(0)

    if symlink:
        doc = yew.store.create_document(title, kind, symlink_source_path=path)
        click.echo("Symlinked: %s" % doc.uid)
    else:
        doc = yew.store.create_document(title, kind)
        doc.put_content(content)
    yew.remote.push_doc(doc)


@cli.command()
@click.argument("name", required=False)
@click.argument("path", required=True)
@click.option("--list_docs", "-l", is_flag=True, required=False)
def attach(name, path, list_docs):
    """Take a file and put into media folder.

    The filename will be stripped of spaces.

    """

    if not os.path.exists(path) or not os.path.isfile(path):
        click.echo("file does not exist: %s" % path)
        sys.exit(1)

    doc = get_document_selection(name, list_docs)

    _, filename = os.path.split(path)
    dest_path = os.path.join(doc.get_media_path(), filename)

    # copy file
    with click.open_file(path, "r") as f_in:
        with click.open_file(dest_path, "w") as f_out:
            f_out.write(f_in.read())


def _configure():
    """Prompt user for settings necessary for remote operations.

    Store in user prefs.
    Skip secret things like tokens and passwords.

    """
    # the preferences need to be in the form:
    #  location.default.username
    for pref in settings.USER_PREFERENCES:
        if "token" in pref or "password" in pref:
            continue
        d = yew.store.prefs.get_user_pref(pref)
        p = pref.split(".")
        i = p[2]
        value = click.prompt("Enter %s" % i, default=d, type=str)
        click.echo(pref + "==" + value)
        yew.store.prefs.put_user_pref(pref, value)


@cli.command()
def configure():
    """Get configuration information from user."""
    _configure()


def _authenticate(username, password):
    """Authenticate with remote and populate local data."""

    r = yew.remote.authenticate_user(data={"username": username, "password": password})
    if r.status_code == 200:
        data = r.json()
        yew.store.prefs.put_user_pref("location.default.username", username)
        yew.store.prefs.put_user_pref("location.default.password", password)
        yew.store.prefs.put_user_pref("location.default.email", data["email"])
        yew.store.prefs.put_user_pref("location.default.first_name", data["first_name"])
        yew.store.prefs.put_user_pref("location.default.last_name", data["last_name"])
        yew.store.prefs.put_user_pref("location.default.token", data["token"])
        click.echo("You authenticated successfully. Try `yd sync`.")
    else:
        click.echo("ERORR: {}, {}".format(r.status_code, r.content))
    return r.status_code


@cli.command()
def authenticate():
    """Authenticate with remote and get token.

    You'll be asked for a username/password.
    If you are successfully authenticated by remote,
    the local system will be configured with the account
    of username.

    """
    username = click.prompt(
        "Enter username ",
        default=yew.store.prefs.get_user_pref("location.default.username"),
        type=str,
    )
    password = click.prompt("Enter password ", hide_input=True, type=str)

    current_username = yew.store.prefs.get_user_pref("location.default.username")
    if current_username and not current_username == username:
        if click.confirm(
            "You entered a username that does not match the current system username. Continue?"
        ):
            pass
        else:
            sys.exit(0)
    _authenticate(username, password)


@cli.command()
def register():
    """Try to setup a new user account on remote."""

    # first make sure we are configured
    _configure()

    # next make sure we have a connection to the server
    if not yew.remote.unauthenticated_ping():
        click.echo("Could not connect")
        sys.exit(1)

    username = yew.store.prefs.get_user_pref("location.default.username")
    email = yew.store.prefs.get_user_pref("location.default.email")
    first_name = yew.store.prefs.get_user_pref("location.default.first_name")
    last_name = yew.store.prefs.get_user_pref("location.default.last_name")
    p = SG(r"[\w\d]{12}").render()
    password = click.prompt(
        "Enter a new password or accept the default ", default=p, type=str
    )
    r = yew.remote.register_user(
        data={
            "username": username,
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }
    )
    if r.status_code == 200:
        data = json.loads(r.content)
        yew.store.prefs.put_user_pref("location.default.token", data["token"])
    else:
        click.echo("Something went wrong")
        click.echo("status code: %s" % r.status_code)
        click.echo("response: %s" % r.content)


@cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--location", required=False)
@click.option("--kind", "-k", required=False)
@click.option(
    "--create", "-c", is_flag=True, required=False, help="Create a new document"
)
@click.option(
    "--append",
    "-a",
    is_flag=True,
    required=False,
    help="Append to an existing document",
)
def read(name, list_docs, location, kind, create, append):
    """Get input from stdin and either create a new document or append to an existing one.

    --create and --append are mutually exclusive.
    --create requires a name.

    """

    if create and append:
        click.echo("create and append are mutually exclusive")
        sys.exit(1)

    if create and not name:
        click.echo("a name must be provided when creating")
        sys.exit(1)

    # f = click.open_file('-','r')
    # f = sys.stdin

    content = ""

    # if sys.stdin.isatty() or True:
    #     content = sys.stdin.read()
    with click.open_file("-", "r", "utf-8") as f:
        content = f.read()

    if not (name or create or append):
        # we'll assume create
        # let's ask for a name
        name = click.prompt("Provide a title for the new document", type=str)
        create = True
        append = False

    # if name, we want to either 1) create new file with that name
    # or 2) we want to append or replace an existing one
    if append:
        doc = get_document_selection(name, list_docs)

    # get the type of file
    # we'll ignore this if appending
    kind_tmp = yew.store.prefs.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp
    else:
        kind = "md"

    if not location:
        location = "default"

    if create or not append:
        doc = yew.store.create_document(name, kind, content=content)
    else:
        s = doc.get_content() + content
        doc.put_content(s)


@cli.command()
def info():

    home = expanduser("~")
    file_path = os.path.join(home, ".yew.d")
    print(f"Python version: {sys.version}")
    print(f"~/.yew.d exists: {os.path.exists(file_path)}")
    print(f"YEWDOC_USER env: {os.getenv('YEWDOC_USER')}")
    print(f"username: {yew.store.username}")
    print(f"doc store: {yew.store.yew_dir}")

    print(f"documents={yew.store.get_counts()}")
    email = None
    data = {yew.store.username: {}}

    for k in USER_PREFERENCES:
        v = yew.store.prefs.get_user_pref(k)
        data = glom.assign(data, f"{yew.store.username}.{k}", v, missing=dict)
        if "password" not in k:
            if k == "location.default.email":
                email = v
            click.echo("%s = %s" % (k, v))
    print(json.dumps(data, indent=4))

    try:
        pypandoc.get_pandoc_formats()
        print("pandoc installed")
    except Exception as e:
        print(f"pandoc not installed: {e}")
    try:
        r = yew.remote.ping()
        if r is not None and r.status_code == 200:
            print(f"remote: {r.content.decode()}")
        else:
            print(f"remote: {f}")
    except Exception as e:
        print(f"remote error: {e}")
    print(f"Encryption: {email}")
    print(f"gnupg dir: {yew.store.get_gnupg_exists()}")
    if yew.store.get_gnupg_exists():
        Args = namedtuple("Args", "gpg_dir")
        args = Args(gpg_dir=".gnupg")
        keys = list_keys(args)
        print("Public keys")
        for public_key in keys[0]:
            for uid in public_key["uids"]:
                print(uid, end="")
                if email in uid:
                    print(" <= identity in use")
                else:
                    print("")
        print("Private keys")
        for private_key in keys[1]:
            for uid in private_key["uids"]:
                print(uid, end="")
                if email in uid:
                    print(" <= identity in use")
                else:
                    print("")
