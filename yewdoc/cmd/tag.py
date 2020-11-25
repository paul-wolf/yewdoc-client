import sys
from collections import defaultdict

import click

from .. import shared

def print_tags(store, tagname):
    stats = defaultdict(int)
    tagged_count = 0
    for data in store.index:
        doc_tags = data.get("tags", list())
        if doc_tags:
            tagged_count += 1
        for t in doc_tags:
            stats[t] += 1
    print(f"Total tagged docs: {tagged_count}")
    for k, v in stats.items():
        if tagname and k != tagname:
            continue
        print(f"{k}: {v}")



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
    """Assign tags.

    Use this command to create tags, associate them with documents and
    remove tags.

    The tag command with no further arguments or options will list all tags.

    """
    yew = ctx.obj["YEW"]

    if not docname:
        print_tags(yew.store, tagname)
        return
    docs = shared.get_document_selection(ctx, docname, list_docs, multiple=True)
    for doc in docs:
        if not untag:
            doc.add_tag(tagname)
        else:
            doc.remove_tag(tagname)
        yew.store.reindex_doc(doc, write_index_flag=False)
    yew.store.write_index()
