import sys
import difflib
from typing import List, Optional, Dict, Union

import click

from .store import YewStore
from .remote import REMOTES
from .remote import Remote
from .utils import (
    is_short_uuid,
    is_uuid,
)
from .actions import ACTION_HANDLERS
from .document import Document

__version__ = "0.2.0"
__author__ = "Paul Wolf"
__license__ = "BSD"


class YewCLI:
    """Wraps two principle classes.

    We manage the store and remote objects.

    """

    def __init__(self, username=None, debug=False):

        self.store = YewStore(username=username)
        if debug:
            print(f"***************** {self.store.username} ************")
        remote_name = self.store.prefs.get_user_pref("location.default.remote_type")
        if not remote_name:
            remote_class = Remote
        else:
            try:
                remote_class = REMOTES[remote_name]
            except KeyError:
                click.echo(f"Could not find {remote_name} as a remote type; choices are: {list(REMOTES.keys())}; check settings.")
                sys.exit(1)
        self.remote = remote_class(self.store)
        self.actions = ACTION_HANDLERS
        if debug:
            print(f"***************** {remote_class.__name__} ************")        


@click.group()
@click.option("--user", help="User name", required=False)
@click.option("--debug", "-d", is_flag=True, help="Debug flag", required=False)
@click.pass_context
def cli(ctx, user, debug):

    yew = YewCLI(username=user, debug=debug)
    ctx.ensure_object(dict)
    ctx.obj["YEW"] = yew
    ctx.obj["DEBUG"] = debug


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


def document_menu(docs, multiple=False) -> List[Document]:
    """Show list of docs. Return selection.

    Multiple means use can provide a range otherwise, 
    a list with a single doc is returned.
    """
    if not len(docs):
        return list()
    
    for index, doc in enumerate(docs):
        click.echo(f"{index}) {doc.name} ({doc.short_uid()})")
    if multiple:
        v = click.prompt("Select document. You can provide ranges.")
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
            return list()

    return [docs[v]]


def get_document_selection(ctx, name, list_docs, tags=None, multiple=False) -> List[Document]:
    """Present lists or whatever to get doc choice.

    name (str): a title or partial title to use as search
    list_docs (bool): a flag to list documents are not.
    multiple (bool): allow range of integers for a list selection

    If there is no name, show recent list.
    otherwise, show all docs

    We let user specify if a list of docs should be returned.
    In that case, the return value's type is a list.

    """
    yew = ctx.obj["YEW"]
    # import ipdb; ipdb.set_trace()
    if name and is_uuid(name):
        return [yew.store.get_doc(name)]

    if name and is_short_uuid(name):
        return [yew.store.get_short(name)]

    if not name and not list_docs and not tags:
        docs = yew.store.get_recent(yew.store.username)
        return document_menu(docs, multiple)
    elif list_docs:
        docs = yew.store.get_docs(name_frag=name, tags=tags)
        if len(docs) == 1:
            return docs
        return document_menu(docs, multiple)
    elif name and not list_docs:
        return yew.store.get_docs(name_frag=name, tags=tags)
    elif name or tags:
        docs = yew.store.get_docs(name_frag=name, tags=tags)
        if len(docs) == 1:
            return docs
        if list_docs:
            return document_menu(docs, multiple)
        else:
            return docs

    return list()


def diff_content(doc1, doc2):
    # d = difflib.Differ()
    # diff = d.compare(doc1,doc2)
    diff = difflib.ndiff(doc1, doc2)
    click.echo("\n".join(list(diff)))
