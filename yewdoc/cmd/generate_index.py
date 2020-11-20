import sys
import json

import click

from .. import shared


@shared.cli.command()
@click.pass_context
def generate_index(ctx):
    """Iterate document directory and output index json to stdout.
    This can be used to replace a damaged or missing index.
    """
    yew = ctx.obj["YEW"]
    data = yew.store.generate_doc_data()
    print(json.dumps(data, indent=4))
