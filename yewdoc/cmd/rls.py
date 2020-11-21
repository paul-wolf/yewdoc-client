import json

import click
from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--info", "-l", is_flag=True, required=False)
@click.option("--humanize", "-h", is_flag=True, required=False)
@click.option("--encrypted", "-e", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.option("--sort", "-s", is_flag=True, required=False)
@click.option("--size", "-S", is_flag=True, required=False)
@click.option("--descending", "-d", is_flag=True, required=False)
@click.pass_context
def rls(ctx, name, info, humanize, encrypted, tags, sort, size, descending):
    """List documents."""
    yew = ctx.obj["YEW"]
    docs = yew.remote.list_docs()
    print(json.dumps(docs, indent=4))
