import sys

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
    print("user-pref, name={}, value={}".format(name, value))

    if name and not value:
        click.echo("%s = %s" % (name, yew.store.prefs.get_user_pref(name)))
    elif name and value:
        yew.store.prefs.put_user_pref(name, value)
    else:
        for k in settings.USER_PREFERENCES:
            v = yew.store.prefs.get_user_pref(k)
            click.echo("%s = %s" % (k, v))
