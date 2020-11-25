import sys
import os
import traceback

import dateutil

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option(
    "--force", "-f", is_flag=True, required=False, help="Don't confirm deletes"
)
@click.option(
    "--prune",
    "-p",
    is_flag=True,
    required=False,
    help="Delete local docs marked as deleted on server",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    required=False,
    help="Print document status even when no change",
)
@click.option(
    "--fake",
    is_flag=True,
    required=False,
    help="Comopare docs but take no action",
)
@click.option(
    "--tags",
    is_flag=True,
    required=False,
    help="Pull tags from server",
)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def sync(ctx, name, force, prune, verbose, fake, tags, list_docs):
    """Pushes local docs and pulls docs from remote.

    We don't overwrite newer docs.
    Does nothing if docs are the same.

    """
    yew = ctx.obj["YEW"]
    yew.remote.sync(name, force, prune, verbose, fake, tags, list_docs)
