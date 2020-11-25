import sys

import click

from ..utils import slugify
from .. import shared

try:
    import pypandoc
except Exception:
    print("pypandoc won't load; convert cmd will not work")


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("destination_format", required=False)
@click.argument("destination_file", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--formats", "-f", is_flag=True, required=False)
@click.pass_context
def convert(ctx, name, destination_format, destination_file, list_docs, formats):
    """Convert to destination_format and print to stdout or save to file if provided."""
    # yew = ctx.obj["YEW"]
    if formats or not destination_format:
        formats = pypandoc.get_pandoc_formats()
        click.echo("Input formats:")
        for f in formats[0]:
            click.echo("\t" + f)
        click.echo("Output formats:")
        for f in formats[1]:
            click.echo("\t" + f)
        sys.exit(0)

    docs = shared.get_document_selection(ctx, name, list_docs)
    if not docs:
        sys.exit(1)
    doc = docs[0]
    click.echo(doc.name)
    click.echo(doc.kind)
    click.echo(destination_format)

    if destination_format in ["docx", "pdf", "odt"]:
        destination_file = "{}.{}".format(slugify(doc.name), destination_format)

    if destination_file:
        dest = pypandoc.convert(
            doc.get_content(),
            format=doc.kind,
            to=destination_format,
            outputfile=destination_file,
        )
        click.echo(destination_file)
    else:
        dest = pypandoc.convert_text(
            doc.get_content(), format=doc.kind, to=destination_format
        )
        click.echo(dest)
    sys.stdout.flush()
