import sys

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option("--remote", "-r", is_flag=True, required=False)
@click.option("--diff", "-d", is_flag=True, required=False)
@click.pass_context
def describe(ctx, name, list_docs, remote, diff):
    """Show document details."""
    yew = ctx.obj["YEW"]
    doc = shared.get_document_selection(ctx, name, list_docs)

    if doc:
        doc.dump()
    status = None
    if remote:
        r_info = yew.remote.doc_exists(doc.uid)
        click.echo("Remote: ")
        for k, v in r_info.items():
            click.echo("%s: %s" % (k, v))
        status = yew.remote.doc_status(doc.uid)
        click.echo(Remote.STATUS_MSG[status])
    if (
        doc
        and diff
        and not status == Remote.STATUS_REMOTE_SAME
        and not Remote.STATUS_NO_CONNECTION
    ):
        remote_doc = yew.remote.fetch(doc.uid)
        s = shared.diff_content(
            remote_doc["content"].rstrip().splitlines(),
            doc.get_content().rstrip().splitlines(),
        )
        click.echo(s)
