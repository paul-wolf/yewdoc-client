import sys

import click

from .. import shared
from ..remote import RemoteStatus


@shared.cli.command()
@click.pass_context
def push(ctx):
    """Push all documents to the server."""
    yew = ctx.obj["YEW"]
    docs = yew.store.get_docs()
    result = ""
    for doc in docs:
        click.echo(f"pushing: {doc.name}", nl=False)
        status = yew.remote.push_doc(doc)
        if status == RemoteStatus.STATUS_REMOTE_SAME:
            result = " No difference"
        elif status == RemoteStatus.STATUS_REMOTE_NEWER:
            result = " can't push because remote newer"
        elif status == RemoteStatus.STATUS_REMOTE_OLDER:
            result = " local newer, pushed"
        elif status == RemoteStatus.STATUS_DOES_NOT_EXIST:
            result = " no remote version, creating"
        click.echo(result)
    click.echo("Done!")
