import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=True)
@click.option(
    "--kind",
    "-k",
    default="md",
    help="Type of document, txt, md, rst, json, etc.",
    required=False,
)
@click.pass_context
def create(ctx, name, kind):
    """Create a new document."""
    yew = ctx.obj["YEW"]

    # get the type of file
    kind_tmp = yew.store.prefs.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp

    doc = yew.store.create_document(name, kind)

    click.echo(f"created document: {doc.uid}, {doc.name}.{doc.kind}")
    click.edit(require_save=True, filename=doc.path)
