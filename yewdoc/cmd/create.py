import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
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
    if not name:
        docs = yew.store.search_names("%s")
        for index, doc in enumerate(docs):
            click.echo("%s [%s]" % (doc.name, doc.kind))

        sys.exit(0)

    # get the type of file
    kind_tmp = yew.store.prefs.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp

    doc = yew.store.create_document(name, kind)

    click.echo("created document: %s" % doc.uid)
    click.edit(require_save=True, filename=doc.path)
    yew.remote.push_doc(yew.store.get_doc(doc.uid))
