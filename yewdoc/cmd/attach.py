import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("path", required=True)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def attach(ctx, name, path, list_docs):
    """Take a file and put into media folder.

    The filename will be stripped of spaces.

    """
    yew = ctx.obj["YEW"]
    if not os.path.exists(path) or not os.path.isfile(path):
        click.echo("file does not exist: %s" % path)
        sys.exit(1)

    doc = shared.get_document_selection(ctx, name, list_docs)

    _, filename = os.path.split(path)
    dest_path = os.path.join(doc.get_media_path(), filename)

    # copy file
    with click.open_file(path, "r") as f_in:
        with click.open_file(dest_path, "w") as f_out:
            f_out.write(f_in.read())
