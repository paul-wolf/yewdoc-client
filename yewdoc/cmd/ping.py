import sys
import datetime

import click
import dateutil

from .. import shared


@shared.cli.command()
@click.pass_context
def ping(ctx):
    """Ping server."""
    yew = ctx.obj["YEW"]
    r = yew.remote.ping()
    if r is None:
        print("No response")
        sys.exit(1)
    if r.status_code == 200:
        print(r.content)
        sdt = dateutil.parser.parse(r.json())
        click.echo("Server time  : %s" % sdt)
        click.echo("Here time    : {}".format(datetime.datetime.now()))
        n = datetime.datetime.now()
        if n > sdt:
            d = n - sdt
        else:
            d = sdt - n
        click.echo("Skew         : %s" % str(d))
        sys.exit(0)
    click.echo("ERROR HTTP code={}, msg={}".format(r.status_code, r.content))
