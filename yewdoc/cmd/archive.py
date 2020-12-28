import sys

import click

from .. import shared


@shared.cli.command()
@click.pass_context
def archive(ctx):
    """Create tgz archive in the current directory of all documents and index and settings. """
    yew = ctx.obj["YEW"]
    print(yew.store.generate_archive())
