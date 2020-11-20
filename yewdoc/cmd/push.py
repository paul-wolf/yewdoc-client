import sys

import click

from .. import shared


@shared.cli.command()
@click.pass_context
def push(ctx):
    """Push all documents to the server."""
    yew = ctx.obj["YEW"]
    if yew.remote.offline:
        pass
    docs = yew.store.get_docs()
    result = ""
    for doc in docs:
        click.echo("pushing: %s:" % doc.name, nl=False)
        status = yew.remote.push_doc(doc)
        if status == Remote.STATUS_REMOTE_SAME:
            result = " No difference"
        elif status == Remote.STATUS_REMOTE_NEWER:
            result = " can't push because remote newer"
        elif status == Remote.STATUS_REMOTE_OLDER:
            result = " local newer, pushed"
        elif status == Remote.STATUS_DOES_NOT_EXIST:
            result = " no remote version, creating"
        click.echo(result)
    click.echo("Done!")
