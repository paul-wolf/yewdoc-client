import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def show(ctx, name, list_docs):
    """Send contents of document to stdout."""
    # yew = ctx.obj["YEW"]

    docs = shared.get_document_selection(ctx, name, list_docs)
    if docs:
        click.echo(docs[0].get_content())
    else:
        click.echo("no matching documents")
    sys.stdout.flush()
