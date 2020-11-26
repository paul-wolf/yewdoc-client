import os
from collections import defaultdict

import click
from .. import shared


@shared.cli.command()
@click.pass_context
def tags(ctx):
    """List all tags."""
    yew = ctx.obj["YEW"]

    stats = defaultdict(int)
    tagged_count = 0
    for data in yew.store.index:
        doc_tags = data.get("tags", list())
        if doc_tags:
            tagged_count += 1
        for t in doc_tags:
            stats[t] += 1
    print(f"Total tagged docs: {tagged_count}")

    for k in sorted(stats):
        print(f"{k}: {stats[k]}")
