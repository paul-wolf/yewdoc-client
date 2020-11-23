import sys
import json

import click

from .. import shared
from .. import settings


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("value", required=False)
@click.pass_context
def user_pref(ctx, name, value):
    """Show or set user preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    yew = ctx.obj["YEW"]
    if name and not value:
        click.echo("%s = %s" % (name, yew.store.prefs.get_user_pref(name)))
    elif name and value:
        yew.store.prefs.put_user_pref(name, value)
    else:
        print(json.dumps(yew.store.prefs.data, indent=4))
