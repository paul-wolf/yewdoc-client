import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("tagname", required=False)
@click.argument("docname", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--untag",
    "-u",
    is_flag=True,
    required=False,
    help="Remove a tag association from document(s)",
)
@click.pass_context
def tag(ctx, tagname, docname, list_docs, untag):
    """Manage tags.

    Use this command to create tags, associate them with documents and
    remove tags.

    The tag command with no further arguments or options will list all tags.

    """
    yew = ctx.obj["YEW"]

    docs = shared.get_document_selection(ctx, docname, list_docs, multiple=True)
    if not isinstance(docs, list):
        docs = [docs]

    for doc in docs:
        if not untag:
            doc.add_tag(tagname)
        else:
            doc.remove_tag(tagname)
        yew.store.reindex_doc(doc, write_index_flag=False)
    yew.store.write_index()
