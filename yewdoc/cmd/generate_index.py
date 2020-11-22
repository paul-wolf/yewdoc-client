import sys
import json

import click

from .. import shared


@shared.cli.command()
@click.option("--write", "-w", is_flag=True, required=False)
@click.pass_context
def generate_index(ctx, write):
    """Iterate document directory and output index json to stdout.
    This can be used to replace a damaged or missing index.
    """
    yew = ctx.obj["YEW"]
    data = yew.store.generate_doc_data(write=write)
    if write:
        print(f"recreated index: {yew.store.yew_dir}/index.json")
    else:
        print(json.dumps(data, indent=4))
