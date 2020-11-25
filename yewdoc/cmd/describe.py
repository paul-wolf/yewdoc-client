import sys
from collections.abc import Iterable

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, default=True, required=False)
@click.option("--diff", "-d", is_flag=True, required=False)
@click.pass_context
def describe(ctx, name, list_docs, diff):
    """Show document details."""
    # yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs)
    for doc in docs:
        doc.dump()
