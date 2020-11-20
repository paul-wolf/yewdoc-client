import sys
import os

import click

from .. import shared


@shared.cli.command()
@click.pass_context
def register(ctx):
    """Try to setup a new user account on remote."""
    yew = ctx.obj["YEW"]
    # first make sure we are configured
    _configure()

    # next make sure we have a connection to the server
    if not yew.remote.unauthenticated_ping():
        click.echo("Could not connect")
        sys.exit(1)

    username = yew.store.prefs.get_user_pref("location.default.username")
    email = yew.store.prefs.get_user_pref("location.default.email")
    first_name = yew.store.prefs.get_user_pref("location.default.first_name")
    last_name = yew.store.prefs.get_user_pref("location.default.last_name")
    p = SG(r"[\w\d]{12}").render()
    password = click.prompt(
        "Enter a new password or accept the default ", default=p, type=str
    )
    r = yew.remote.register_user(
        data={
            "username": username,
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }
    )
    if r.status_code == 200:
        data = json.loads(r.content)
        yew.store.prefs.put_user_pref("location.default.token", data["token"])
    else:
        click.echo("Something went wrong")
        click.echo("status code: %s" % r.status_code)
        click.echo("response: %s" % r.content)
