import os
import json
import sys
import datetime
from os.path import expanduser

import glom
import click
import dateutil

from .. import shared
from ..settings import USER_PREFERENCES


@shared.cli.command()
@click.pass_context
def info(ctx):
    yew = ctx.obj["YEW"]

    home = expanduser("~")
    file_path = os.path.join(home, ".yew.d")
    print(f"Python version: {sys.version}")
    print(f"~/.yew.d exists: {os.path.exists(file_path)}")
    print(f"YEWDOC_USER env: {os.getenv('YEWDOC_USER')}")
    print(f"username: {yew.store.username}")
    print(f"doc store: {yew.store.yew_dir}")

    print(f"documents={yew.store.get_counts()}")
    email = None
    data = {yew.store.username: {}}

    for k in USER_PREFERENCES:
        v = yew.store.prefs.get_user_pref(k)
        data = glom.assign(data, f"{yew.store.username}.{k}", v, missing=dict)
        if "password" not in k:
            if k == "location.default.email":
                email = v
            click.echo("%s = %s" % (k, v))
    print(json.dumps(data, indent=4))

    try:
        pypandoc.get_pandoc_formats()
        print("pandoc installed")
    except Exception as e:
        print(f"pandoc not installed: {e}")
    try:
        r = yew.remote.ping()
        if r is not None and r.status_code == 200:
            print(f"remote: {r.content.decode()}")
        else:
            print(f"remote: {f}")
    except Exception as e:
        print(f"remote error: {e}")
    print(f"Encryption: {email}")
    print(f"gnupg dir: {yew.store.get_gnupg_exists()}")
    if yew.store.get_gnupg_exists():
        Args = namedtuple("Args", "gpg_dir")
        args = Args(gpg_dir=".gnupg")
        keys = list_keys(args)
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
