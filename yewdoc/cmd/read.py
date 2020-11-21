import os
import sys

import click

from .. import shared


@shared.cli.command()
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
@click.pass_context
def read(ctx, name, list_docs, location, kind, create, append):
    """Get input from stdin and either create a new document or append to an existing one.

    --create and --append are mutually exclusive.
    --create requires a name.

    """
    yew = ctx.obj["YEW"]

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

    name = name.replace(os.sep, "-")
    # if name, we want to either 1) create new file with that name
    # or 2) we want to append or replace an existing one
    if append:
        doc = shared.get_document_selection(ctx, name, list_docs)

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
