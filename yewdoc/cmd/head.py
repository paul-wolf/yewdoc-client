import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def head(ctx, name, list_docs):
    """Send start of document to stdout."""
    yew = ctx.obj["YEW"]
    doc = shared.get_document_selection(ctx, name, list_docs)
    click.echo(doc.get_content()[:250])
