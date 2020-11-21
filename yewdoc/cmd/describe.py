import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--diff", "-d", is_flag=True, required=False)
@click.pass_context
def describe(ctx, name, list_docs, diff):
    """Show document details."""
    yew = ctx.obj["YEW"]
    doc = shared.get_document_selection(ctx, name, list_docs)

    if doc:
        doc.dump()

    
