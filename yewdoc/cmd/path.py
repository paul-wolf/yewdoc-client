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
    doc = shared.get_document_selection(ctx, name, list_docs)
    click.echo(doc.path)
