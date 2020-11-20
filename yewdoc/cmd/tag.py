import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("tagname", required=False)
@click.argument("docname", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--create", "-c", is_flag=True, required=False)
@click.option(
    "--untag",
    "-u",
    is_flag=True,
    required=False,
    help="Remove a tag association from document(s)",
)
@click.pass_context
def tag(ctx, tagname, docname, list_docs, create, untag):
    """Manage tags.

    Use this command to create tags, associate them with documents and
    remove tags.

    The tag command with no further arguments or options will list all tags.

    """
    yew = ctx.obj["YEW"]

    tag = None
    if tagname:
        tagname = tagname.lower()
    if tagname and create:
        tag = yew.store.get_or_create_tag(tagname)
        click.echo("created: %s %s" % (tag.tagid, tag.name))
    elif create and not tagname:
        click.echo("tag name required")
    elif tagname and docname:
        if not tag:
            tags = yew.store.get_tags(tagname, exact=True)
        if len(tags) > 0:
            tag = tags[0]
        if not tag:
            click.echo("No tags found")
            sys.exit(0)
        docs = shared.get_document_selection(ctx, docname, list_docs, multiple=True)
        if docs and isinstance(docs, list):
            for doc in docs:
                if untag:
                    yew.store.dissociate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s removed" % (tag.name, doc.name))
                else:
                    yew.store.associate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s" % (tag.name, doc.name))
        elif docs:
            doc = docs
            if untag:
                yew.store.dissociate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s removed" % (tag.name, doc.name))
            else:
                yew.store.associate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s" % (tag.name, doc.name))
    else:
        # list tags
        tags = yew.store.get_tags(tagname)
        for tag in tags:
            click.echo(tag.name)
