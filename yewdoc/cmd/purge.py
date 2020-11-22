import sys

import click
from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.pass_context
def purge(ctx, name, list_docs, force):
    """Delete documents of zero size.

    provide a name fragment to filter.

    """
    yew = ctx.obj["YEW"]
    docs = yew.store.get_docs(name_frag=name)

    docs = list(filter(lambda d: d.size == 0, docs))
    for doc in docs:
        click.echo(f"{doc.uid}, {doc.name}")
    d = True
    if not force:
        d = click.confirm("Do you want to continue to delete the document(s)?")
    if d:
        for doc in docs:
            yew.store.delete_document(doc)
