import click

from .. import shared


@shared.cli.command()
@click.pass_context
def status(ctx):
    """Print info about current setup."""
    yew = ctx.obj["YEW"]
    click.echo("Version  : %s" % shared.__version__)
    click.echo("User     : %s" % yew.store.username)
    click.echo("Storage  : %s" % yew.store.yew_dir)
    click.echo("Offline  : %s" % yew.store.offline)
