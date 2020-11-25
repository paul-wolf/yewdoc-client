import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("new_name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def rename(ctx, name, new_name, list_docs):
    """Rename a document."""
    yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs)
    if not docs:
        sys.exit(1)
    doc = docs[0]
    if not new_name:
        click.echo("Rename: '%s'" % doc.name)
        new_name = click.prompt("Enter the new document title ", type=str)
    if new_name:
        doc = yew.store.rename_doc(doc, new_name)

