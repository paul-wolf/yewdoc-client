import sys
import os
import traceback

import dateutil

import click

from .. import shared
from ..remote import Remote, OfflineException, RemoteException, RemoteStatus, STATUS_MSG
from ..document import deserialize


def pdoc(doc, status, verbose):
    """Print status to stdout."""

    if status == RemoteStatus.STATUS_REMOTE_SAME and not verbose:
        print(".", end="", flush=True)
    else:
        click.echo("", nl=True)
        click.echo(doc.name, nl=False)
        msg = STATUS_MSG[status]
        click.echo(": ", nl=False)
        click.secho(msg, fg="yellow")


def remote_doc_status(doc, remote_index) -> RemoteStatus:

    docs = list(filter(lambda d: d["uid"] == doc.uid, remote_index))
    if not docs:
        return RemoteStatus.STATUS_DOES_NOT_EXIST
    if doc.is_symlink:
        return RemoteStatus.STATUS_UNKNOWN  # we don't modify links during sync
    doc_remote = docs[0]
    doc_remote_updated = dateutil.parser.parse(doc_remote["date_updated"])
    if doc.digest == doc_remote["digest"]:
        return RemoteStatus.STATUS_REMOTE_SAME
    if doc.updated > doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_OLDER
    if doc.updated < doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_NEWER

    return RemoteStatus.STATUS_UNKNOWN


@shared.cli.command()
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
@click.option(
    "--fake",
    is_flag=True,
    required=False,
    help="Comopare docs but take no action",
)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def sync(ctx, name, force, prune, verbose, fake, list_docs):
    """Pushes local docs and pulls docs from remote.

    We don't overwrite newer docs.
    Does nothing if docs are the same.

    """
    yew = ctx.obj["YEW"]
    v = verbose
    # make sure we are online
    try:
        r = yew.remote.ping()
    except OfflineException:
        click.echo("can't sync in offline mode")

    if name:
        doc = shared.get_document_selection(ctx, name, list_docs)
        docs_local = [doc]
    else:
        docs_local = yew.store.get_docs()
    remote_done = []
    deleted_index = yew.store.get_deleted_index()
    remote_index = yew.remote.list_docs()

    for doc in docs_local:
        try:
            c = remote_doc_status(doc, remote_index)
            remote_done.append(doc.uid)
            if c == RemoteStatus.STATUS_REMOTE_SAME:
                pdoc(doc, c, v)
                continue
            elif c == RemoteStatus.STATUS_REMOTE_NEWER:
                if not fake:
                    remote_doc = yew.remote.fetch_doc(doc.uid)
                    doc.put_content(remote_doc["content"])
                    if not remote_doc["title"] == doc.name:
                        yew.store.rename_doc(doc, remote_doc["title"])
                pdoc(doc, c, v)
                remote_done.append(doc.uid)
                continue
            elif c == RemoteStatus.STATUS_REMOTE_OLDER:
                if not fake:
                    status_code = yew.remote.push_doc(doc)
                else:
                    status_code = 200
                if status_code == 200:
                    pdoc(doc, c, v)
                else:
                    click.secho(f"push failed: {doc}, {status_code}", fg="red")

                remote_done.append(doc.uid)
                continue
            elif c == RemoteStatus.STATUS_DOES_NOT_EXIST:
                if not fake:
                    status_code = yew.remote.push_doc(doc)
                else:
                    status_code = 200
                if r.status_code == 200:
                    pdoc(doc, c, v)
                else:
                    click.secho("pushed failed", fg="red")
                remote_done.append(doc.uid)
            elif c == RemoteStatus.STATUS_REMOTE_DELETED:
                if prune:
                    if not fake:
                        yew.store.delete_document(doc)
                    pdoc(doc, c, v)
                else:
                    pdoc(doc, c, v)
                continue
            elif c == RemoteStatus.STATUS_UNKNOWN:
                # this happens for symlinks for instance
                pdoc(doc, c, v)
            else:
                raise Exception("Invalid remote status   : %s for %s" % (c, str(doc)))
        except Exception as e:
            print(f"An error occured trying to sync {doc}")
            traceback.print_exc()
    print("")

    # if we chose to update a single doc, we are done, no tag updates or anything else
    # because remote_done won't have values for the follow step to make sense
    if name:
        return

    for rdoc in remote_index:
        if rdoc["uid"] in remote_done:
            continue

        if not fake and rdoc["uid"] not in deleted_index:
            click.echo(f"importing doc: {rdoc['uid'].split('-')[0]} {rdoc['title']}")
            remote_doc = yew.remote.fetch_doc(rdoc["uid"])
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
