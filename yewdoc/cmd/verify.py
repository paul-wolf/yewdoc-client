import sys

import click

from .. import shared


@shared.cli.command()
@click.option("--prune", "-p", is_flag=True, required=False)
@click.pass_context
def verify(ctx, prune=False):
    """Check docs exist."""
    yew = ctx.obj["YEW"]
    missing = yew.store.verify_docs(prune=prune)
    if prune and missing:
        print("Removed missing")
    if not missing:
        print("No missing docs")
