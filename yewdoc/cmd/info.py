import os
import json
import sys
import datetime
from os.path import expanduser
from collections import namedtuple
import getpass

import glom
import click
import dateutil
import gnupg

from .. import shared
from ..settings import USER_PREFERENCES

try:
    import pypandoc
except Exception:
    print("pypandoc won't load; convert cmd will not work")


@shared.cli.command()
@click.pass_context
def info(ctx):
    """Provide configuration information."""
    yew = ctx.obj["YEW"]

    home = expanduser("~")
    yew_dir_path = os.path.join(home, ".yew.d")
    yew_path = os.path.join(home, ".yew")
    v = sys.version.replace("\n", " ")
    print(f"document count       : {yew.store.get_counts()}")
    print(f"User                 : {yew.store.username}")
    print(f"Python version       : {v}")
    print(f"~/.yew exists        : {os.path.exists(yew_path)}")
    print(f"~/.yew.d exists      : {os.path.exists(yew_dir_path)}")
    print(f"YEWDOC_USER env      : {os.getenv('YEWDOC_USER')}")
    print(f"username             : {yew.store.username}")
    print(f"doc store            : {yew.store.yew_dir}")

    email = None
    data = {}

    for k in USER_PREFERENCES:
        v = yew.store.prefs.get_user_pref(k)
        data = glom.assign(data, f"{k}", v, missing=dict)
        if "password" not in k:
            if k == "location.default.email":
                email = v
            click.echo(f"{k.ljust(30)}: {v}")
    print(json.dumps(data, indent=4))

    try:
        pypandoc.get_pandoc_formats()
        print("pandoc installed")
    except Exception as e:
        print(f"pandoc not installed: {e}")
    try:
        r = yew.remote.ping()
        if r is not None and r.status_code == 200:
            print(f"remote time: {r.content.decode()}")
        else:
            print(f"remote: {r}")
    except Exception as e:
        print(f"remote error: {e}")
    print(f"Encryption  : {email}")
    print(f"gnupg dir   : {yew.store.get_gnupg_exists()}")
    if yew.store.get_gnupg_exists():
        gpg = gnupg.GPG(gnupghome="/path/to/home/directory")
        Args = namedtuple("Args", "gpg_dir")
        args = Args(gpg_dir=".gnupg")
        keys = gpg.list_keys(args)
        print("Public keys")
        for public_key in keys[0]:
            for uid in public_key["uids"]:
                print(uid, end="")
                if email in uid:
                    print(" <= identity in use")
                else:
                    print("")
        print("Private keys")
        for private_key in keys[1]:
            for uid in private_key["uids"]:
                print(uid, end="")
                if email in uid:
                    print(" <= identity in use")
                else:
                    print("")
