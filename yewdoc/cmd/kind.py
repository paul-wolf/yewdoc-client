import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("kind", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def kind(ctx, name, kind, list_docs):
    """Change kind of document."""
    yew = ctx.obj["YEW"]
    doc = shared.get_document_selection(ctx, name, list_docs)
    if not kind:
        click.echo(doc)
        click.echo("Current document kind: '%s'" % doc.kind)
        for i, d in enumerate(DOC_KINDS):
            click.echo("%s" % (d))
        kind = click.prompt("Select the new document kind ", type=str)
    click.echo("Changing document kind to: %s" % kind)
    doc = yew.store.change_doc_kind(doc, kind)
    try:
        yew.remote.push_doc(doc)
    except Exception as e:
        print(e)
    sys.exit(0)
