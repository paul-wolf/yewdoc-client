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
    help="Your GnuGPG home directory, defaults to .gnupg",
)
@click.pass_context
def encrypt(ctx, name, list_docs, gpghome):
    """Encrypt a document."""
    yew = ctx.obj["YEW"]
    docs = shared.get_document_selection(ctx, name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not docs:
        sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")
    doc = docs[0]
    
    # try to encrypt in place
    crypt.encrypt_file(doc.get_path(), email, gpghome)

    yew.store.prefs.put_user_pref("current_doc", doc.uid)
    yew.store.update_recent("yewser", doc)
