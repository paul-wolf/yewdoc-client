import os

import humanize as h
import click
from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--info", "-l", required=False, count=True)
@click.option("--humanize", "-h", is_flag=True, required=False)
@click.option("--exact", "-e", is_flag=True, required=False)
@click.option("--tags", "-t", required=False)
@click.option("--sort", "-s", is_flag=True, required=False)
@click.option("--size", "-S", is_flag=True, required=False)
@click.option("--descending", "-d", is_flag=True, required=False)
@click.pass_context
def ls(ctx, name, info, humanize, exact, tags, sort, size, descending):
    """List documents."""
    yew = ctx.obj["YEW"]

    tags = tags.split(",") if tags else list()
    docs = yew.store.get_docs(name_frag=name, tags=tags, exact=exact)
    if not docs:
        return
    if sort or size or descending:
        if size:
            docs.sort(key=lambda doc: doc.size, reverse=descending)
    else:
        docs.sort(key=lambda doc: doc.updated, reverse=descending)

    for doc in docs:
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

        click.echo(click.style(doc.name, fg='green'), nl=False)
        if info > 1:
            click.echo("")
            print(doc.get_content()[:250])
        click.echo("")
