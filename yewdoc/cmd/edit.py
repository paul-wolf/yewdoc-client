import sys
import os

import click

from .. import shared


@shared.cli.command()
@click.argument("name", required=False)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.option(
    "--open-file",
    "-o",
    is_flag=True,
    required=False,
    help="Open the file in your host operating system.",
)
@click.option(
    "--gpghome",
    "-g",
    required=False,
    default=".gnupg",
    help="Your GnuGPG home directory, defaults to .gnupg",
)
@click.pass_context
def edit(ctx, name, list_docs, open_file, gpghome):
    """Edit a document.

    Set your $EDITOR environment variable to determine what editor
    will handle the file.

    When the editor is closed, the file will sync to the server
    if you are registered with a Yewdoc cloud instance
    (and if not working offline).

    --open-file will send the document to the host operating system
    for it to decide how to open the file. Since using this option
    means the editor is not a child process, you need to manually sync
    with remote to push changes.

    """
    yew = ctx.obj["YEW"]
    doc = shared.get_document_selection(ctx, name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not doc:
        if click.confirm("Couldn't find that document, shall we create it?"):
            doc = yew.store.create_document(name, kind="md")
        else:
            sys.exit(0)

    email = yew.store.prefs.get_user_pref("location.default.email")

    encrypted = doc.check_encrypted()
    if encrypted:
        decrypt_file(doc.get_path(), email, gpghome)
    if open_file:
        # send to host os to ask it how to open file
        click.launch(doc.get_path())
    else:
        click.edit(editor="emacs", require_save=True, filename=doc.path)

    if encrypted:
        encrypt_file(doc.get_path(), email, gpghome)

    # yew.store.prefs.put_user_pref("current_doc", doc.uid)
    # yew.store.prefs.update_recent(doc)
