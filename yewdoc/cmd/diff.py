import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name1", required=True)
@click.argument("name2", required=True)
@click.pass_context
def diff(ctx, name1, name2):
    """Compare two documents."""
    yew = ctx.obj["YEW"]
    doc1 = shared.get_document_selection(ctx, name1, list_docs=False)
    doc2 = shared.get_document_selection(ctx, name2, list_docs=False)
    """Compare two documents."""

    s = shared.diff_content(
        doc1.get_content().rstrip().splitlines(),
        doc2.get_content().rstrip().splitlines(),
    )
    click.echo(s)
