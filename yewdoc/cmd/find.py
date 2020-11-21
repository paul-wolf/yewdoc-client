import sys
import re

import click

from .. import shared


@shared.cli.command()
@click.argument("spec", required=True)
@click.option("--string-only", "-s", is_flag=True, required=False)
@click.option("--insensitive", "-i", is_flag=True, required=False)
@click.pass_context
def find(ctx, spec, string_only, insensitive):
    """Search for spec in contents of docs.

    spec is a regular expression unless string-only is selected
    in which case a simple string match is used.

    """
    yew = ctx.obj["YEW"]

    docs = yew.store.get_docs()

    for doc in docs:
        found = False
        if string_only:
            if not insensitive:
                if spec in doc.get_content():
                    found = True
            else:
                if spec.lower() in doc.get_content().lower():
                    found = True
        elif re.search(spec, doc.get_content()):
            found = True

        if found:
            click.echo(doc.name)
