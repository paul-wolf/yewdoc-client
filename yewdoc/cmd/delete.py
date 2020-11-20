import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
@click.pass_context
def delete(ctx, name, list_docs, force, remote):
    """Delete a document.

    To delete a remote document, it needs to be local. So,
    you may need to sync it from remote before deleting it.

    """
    yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs, multiple=True)
    if not docs:
        click.echo("no matching documents")
        return
    if not isinstance(docs, list):
        docs = [docs]
    for doc in docs:
        click.echo("Document: %s  %s" % (doc.uid, doc.name))
    d = True
    if not force:
        d = click.confirm("Do you want to continue to delete the document(s)?")
    if d:
        for doc in docs:
            yew.store.delete_document(doc)
            if remote:
                yew.remote.delete("document/%s" % doc.uid)
                click.echo("removed %s" % doc.name)
