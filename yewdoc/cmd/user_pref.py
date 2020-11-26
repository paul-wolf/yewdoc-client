import sys
import json

import click

from .. import shared
from .. import settings


@shared.cli.command()
@click.argument("name", required=False)
@click.argument("value", required=False)
@click.option("--delete", "-d", is_flag=True)
@click.pass_context
def user_pref(ctx, name, value, delete):
    """Show or set user preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    yew = ctx.obj["YEW"]
    if name and not value:
        if delete:
            yew.store.prefs.delete_user_pref(name)
            click.echo(f"deleted user pref {name}")
        else:
            v = yew.store.prefs.get_user_pref(name)
            click.echo(f"{name} = {v}")
    elif name and value:
        yew.store.prefs.put_user_pref(name, value)
    else:
        print(json.dumps(yew.store.prefs.data, indent=4))
