import os

import click
from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--info", "-l", is_flag=True, required=False)
@click.option("--humanize", "-h", is_flag=True, required=False)
@click.option("--encrypted", "-e", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.option("--sort", "-s", is_flag=True, required=False)
@click.option("--size", "-S", is_flag=True, required=False)
@click.option("--descending", "-d", is_flag=True, required=False)
@click.pass_context
def ls(ctx, name, info, humanize, encrypted, tags, sort, size, descending):
    """List documents."""
    yew = ctx.obj["YEW"]

    tag_objects = []
    if tags:
        tag_objects = yew.store.parse_tags(tags)
    else:
        # check for context
        current_tag_context = yew.store.prefs.get_user_pref("tag_context")
        if current_tag_context:
            tag_objects = [yew.store.get_tag(current_tag_context)]
            click.echo("Current tag context: %s" % str(tag_objects[0]))
    if name:
        docs = yew.store.search_names(name, encrypted=encrypted)
    else:
        docs = yew.store.get_docs(tag_objects=tag_objects, encrypted=encrypted)

    if sort or size or descending:
        if size:
            docs.sort(key=lambda doc: doc.size, reverse=descending)
    else:
        docs.sort(key=lambda doc: doc.updated, reverse=descending)

    data = []
    for doc in docs:
        # data.append(doc.serialize(no_content=True))
        if info:
            if doc.is_link():
                click.echo("ln ", nl=False)
            else:
                click.echo("   ", nl=False)
            click.echo(doc.short_uid(), nl=False)
            click.echo("   ", nl=False)
            click.echo(doc.kind.rjust(5), nl=False)
            click.echo("   ", nl=False)
            if not os.path.exists(doc.path):
                click.echo("File does not exist")
                continue

            if humanize:
                click.echo(h.naturalsize(doc.get_size()).rjust(10), nl=False)
            else:
                click.echo(str(doc.get_size()).rjust(10), nl=False)
            click.echo("   ", nl=False)
            if humanize:
                click.echo(
                    h.naturaltime(
                        doc.get_last_updated_utc().replace(tzinfo=None)
                    ).rjust(15),
                    nl=False,
                )
            else:
                click.echo(
                    doc.get_last_updated_utc()
                    .replace(microsecond=0)
                    .replace(tzinfo=None),
                    nl=False,
                )
            if doc.is_encrypted():
                click.echo(" (E)", nl=False)
            else:
                click.echo("    ", nl=False)


        click.echo(doc.name, nl=False)
        if info:
            click.echo("   ", nl=False)
            # click.echo(slugify(doc.name), nl=False)
        click.echo("")
