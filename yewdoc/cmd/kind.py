import sys

import click

from .. import shared
from .. import document


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("kind", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def kind(ctx, name, kind, list_docs):
    """Change kind of document."""
    yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs)
    if not docs:
        return
    doc = docs[0]
    if not kind:
        click.echo(doc)
        click.echo(f"Current document kind: '{doc.kind}'")
        for k in document.DOC_KINDS:
            click.echo(k)
        kind = click.prompt("Select the new document kind ", type=str)
    click.echo(f"Changing document kind to: {kind}")
    yew.store.change_doc_kind(doc, kind)
