import sys

import click

from .. import shared
from .. import settings


def _configure(yew):
    """Prompt user for settings necessary for remote operations.

    Store in user prefs.
    Skip secret things like tokens and passwords.

    """
    # the preferences need to be in the form:
    #  location.default.username
    for pref in settings.USER_PREFERENCES:
        if "token" in pref or "password" in pref:
            continue
        d = yew.store.prefs.get_user_pref(pref)
        p = pref.split(".")
        i = p[2]
        value = click.prompt("Enter %s" % i, default=d, type=str)
        click.echo(pref + "==" + value)
        yew.store.prefs.put_user_pref(pref, value)


@shared.cli.command()
@click.pass_context
def configure(ctx):
    """Get configuration information from user."""
    _configure(ctx.obj["YEW"])
