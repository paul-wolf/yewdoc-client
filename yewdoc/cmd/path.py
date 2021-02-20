import os
import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def path(ctx, name, list_docs):
    """Show local disk path for document."""
    # yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs)
    if not docs:
        sys.exit(1)
    click.echo(docs[0].path)
