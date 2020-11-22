import os

import humanize as h
import click
from .. import shared


@shared.cli.command()
@click.argument("action_name", required=False)
@click.argument("name", required=False)
@click.option("--exact", "-e", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.pass_context
def apply(ctx, action_name, name, exact, tags):
    """List documents."""
    yew = ctx.obj["YEW"]

    tags = tags.split(",") if tags else list()
    docs = yew.store.get_docs(name_frag=name, tags=tags, exact=exact)
    if not docs:
        return
    if action_name not in yew.actions:
        print(f"Can't find that action: {action_name}")
    for doc in docs:
        yew.actions[action_name](doc, yew.store, yew.remote)
