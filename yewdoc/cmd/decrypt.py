import sys

import click

from .. import shared
from .. import crypt


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--gpghome",
    "-g",
    required=False,
    default=".gnupg",
    help="Your GnuGPG home directory, defaults to ",
)
@click.pass_context
def decrypt(ctx, name, list_docs, gpghome):
    """Decrypt a document."""
    yew = ctx.obj["YEW"]

    docs = shared.get_document_selection(ctx, name, list_docs)


    if not docs:
        sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")

    # try to decrypt in place
    for doc in docs:
        crypt.decrypt_file(doc.get_path(), email, gpghome)
        # yew.store.prefs.put_user_pref("current_doc", doc.uid)
        # yew.store.update_recent("yewser", doc)
