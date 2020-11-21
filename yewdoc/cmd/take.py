import sys
import os

import click

from .. import shared


@shared.cli.command()
@click.argument("path", required=True)
@click.option("--kind", "-k", required=False)
@click.option("--force", "-f", is_flag=True, required=False)
@click.option("--symlink", "-s", is_flag=True, required=False)
@click.pass_context
def take(ctx, path, kind, force, symlink):
    """Import a file as a document.

    The base filename becomes the document title.

    Should be a text type, but we leave that to user.

    --force will cause a similarly titled document to be overwritten
    in the case of a name conflict.

    """
    yew = ctx.obj["YEW"]
    # import ipdb; ipdb.set_trace()
    if not os.path.exists(path):
        click.echo(f"path does not exist: {path}")
        sys.exit(1)
    if not os.path.isfile(path):
        click.echo(f"path is not a file: {path}")
        sys.exit(1)

    content = None

    # slurp file
    if not symlink:
        with click.open_file(path, "r", "utf-8") as f:
            content = f.read()

    # get location, filename, etc.
    fn = os.path.basename(path)
    filename, file_extension = os.path.splitext(fn)
    if not kind:
        kind = "txt"
    title = os.path.splitext(path)[0]
    title = title.replace(os.sep, "-")
    # check if we have one with this title
    # the behaviour we want is for the user to continuously
    # ingest the same file that might be updated out-of-band
    # TODO: handle multiple titles of same name
    docs = yew.store.search_names(title, exact=True)
    if docs and not symlink:
        if len(docs) >= 1:
            if not force:
                click.echo("A document with this title exists already")
            if force or click.confirm(
                f"Overwrite existing document: {docs[0].name} ?", abort=True
            ):
                docs[0].put_content(content)
                sys.exit(0)

    if symlink:
        doc = yew.store.create_document(title, kind, symlink_source_path=path)
        click.echo(f"Symlinked: {doc.uid}")
    else:
        doc = yew.store.create_document(title, kind)
        doc.put_content(content)
