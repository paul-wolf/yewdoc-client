import sys

import click

from .. import shared


def _authenticate(ctx, username, password):
    """Authenticate with remote and populate local data."""
    yew = ctx.obj["YEW"]
    r = yew.remote.authenticate_user(data={"username": username, "password": password})
    if r.status_code == 200:
        data = r.json()
        yew.store.prefs.put_user_pref("location.default.username", username)
        yew.store.prefs.put_user_pref("location.default.password", password)
        yew.store.prefs.put_user_pref("location.default.email", data["email"])
        yew.store.prefs.put_user_pref("location.default.first_name", data["first_name"])
        yew.store.prefs.put_user_pref("location.default.last_name", data["last_name"])
        yew.store.prefs.put_user_pref("location.default.token", data["token"])
        click.echo("You authenticated successfully. Try `yd sync`.")
    else:
        click.echo("ERORR: {}, {}".format(r.status_code, r.content))
    return r.status_code


@shared.cli.command()
@click.pass_context
def authenticate(ctx):
    """Authenticate with remote and get token.

    You'll be asked for a username/password.
    If you are successfully authenticated by remote,
    the local system will be configured with the account
    of username.

    """
    yew = ctx.obj["YEW"]
    username = click.prompt(
        "Enter username ",
        default=yew.store.prefs.get_user_pref("location.default.username"),
        type=str,
    )
    password = click.prompt("Enter password ", hide_input=True, type=str)

    current_username = yew.store.prefs.get_user_pref("location.default.username")
    if current_username and not current_username == username:
        if click.confirm(
            "You entered a username that does not match the current system username. Continue?"
        ):
            pass
        else:
            sys.exit(0)
    _authenticate(ctx, username, password)
