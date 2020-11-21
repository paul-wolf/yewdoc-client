import sys
import json

import click

from .. import shared


@shared.cli.command()
@click.pass_context
def api(ctx):
    """Get API of the server."""
    yew = ctx.obj["YEW"]
    r = yew.remote.api()
    if not r:
        sys.exit(1)
    if r.status_code == 200:
        # content should be server time
        s = json.dumps(r.json(), sort_keys=True, indent=4, separators=(",", ": "))
        click.echo(s)
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)
