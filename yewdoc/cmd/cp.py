import os
import sys
import shutil 
from pathlib import Path

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("destination", required=False)
@click.option("--tags", "-t", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.option("--preserve", "-p", is_flag=True, required=False)
@click.pass_context
def cp(ctx, name, destination, tags, list_docs=False, force=False, preserve=False):
    """Copy one or more docs to destination."""
    yew = ctx.obj["YEW"]
    # import ipdb; ipdb.set_trace()
    if name and not destination:
        destination = name
        name = None
        
    
    if not os.path.exists(destination):
        print("Cannot find {destination}")
        sys.exit(1)
    if not os.path.isdir(destination):
        print("Destination must be a directory")

    tags = tags.split(",") if tags else list()
    docs = shared.get_document_selection(ctx, name, list_docs, tags, multiple=True)
        
    if not force:
        for doc in docs:
            click.echo(doc.name)
    
    if force or click.confirm("Copy documents to {destination}? "):
        for doc in docs:
            print(f"{doc.path} => {destination}")
            cp_func = shutil.copy2 if preserve else shutil.copy
            cp_func(doc.path, Path(destination) / doc.filename)
