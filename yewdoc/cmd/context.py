import sys

import click

from .. import shared


@shared.cli.command()
@click.option("--tag", "-t", required=False, help="Set a tag as a filter.")
@click.option("--clear", "-c", is_flag=True, required=False, help="Clear the context.")
@click.pass_context
def context(ctx, tag, clear):
    """Set or unset a tag context filter for listings.

    A context is essentially a filter. When a context, like a tag is
    set, operations that list documents will filter the
    documents. Like the `ls` command with a context of `-t foo` will
    only list documents tagged with `foo`.

    Use `--clear` to clear the context.

    Currently, only a single tag is allowed for context.

    """
    yew = ctx.obj["YEW"]
    tags = None
    current_tag_context = yew.store.prefs.get_user_pref("tag_context")
    if tag:
        # lookup tag
        tags = yew.store.get_tags(tag, exact=True)
        if not tags:
            click.echo("Tag not found; must be exact match")
            sys.exit(1)
        elif len(tags) > 1:
            click.echo(
                "More than one tag found. Only one tag allowed. Tags matching: %s"
                % ", ".join(tags)
            )
            sys.exit(1)
        yew.store.put_user_pref("tag_context", tags[0].tagid)
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")

    if clear:
        yew.store.prefs.delete_user_pref("tag_context")
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")

    if current_tag_context:
        click.echo("current tag context: %s" % yew.store.get_tag(current_tag_context))
