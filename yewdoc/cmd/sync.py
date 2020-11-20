import sys
import os

import click

from .. import shared
from ..remote import Remote, OfflineException, RemoteException


def pdoc(doc, status, verbose):
    """Print status to stdout."""

    if status == Remote.STATUS_REMOTE_SAME and not verbose:
        print(".", end="", flush=True)
    else:
        click.echo("", nl=True)
        click.echo(doc.name, nl=False)
        msg = Remote.STATUS_MSG[status]
        click.echo(": ", nl=False)
        click.secho(msg, fg="yellow")


@shared.cli.command()
@click.argument("name", required=False)
@click.option(
    "--force", "-f", is_flag=True, required=False, help="Don't confirm deletes"
)
@click.option(
    "--prune",
    "-p",
    is_flag=True,
    required=False,
    help="Delete local docs marked as deleted on server",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    required=False,
    help="Print document status even when no change",
)
@click.option("--list_docs", "-l", is_flag=True, required=False)
@click.pass_context
def sync(ctx, name, force, prune, verbose, list_docs):
    """Pushes local docs and pulls docs from remote.

    We don't overwrite newer docs.
    Does nothing if docs are the same.

    """
    yew = ctx.obj["YEW"]
    v = verbose
    # make sure we are online
    try:
        r = yew.remote.ping()
    except OfflineException:
        click.echo("can't sync in offline mode")

    if name:
        doc = shared.get_document_selection(ctx, name, list_docs)
        docs_local = [doc]
    else:
        docs_local = yew.store.get_docs()
    remote_done = []

    for doc in docs_local:
        try:
            c = yew.remote.doc_status(doc.uid)
            if c == Remote.STATUS_REMOTE_SAME:
                pdoc(doc, c, v)
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_NEWER:
                # click.echo("get newer content from remote: %s %s" % (doc.short_uid(), doc.name))

                remote_doc = yew.remote.fetch(doc.uid)
                # a dict
                doc.put_content(remote_doc["content"])
                if not remote_doc["title"] == doc.name:
                    yew.store.rename_doc(doc, remote_doc["title"])
                #  click.secho("got remote", fg='green')
                pdoc(doc, c, v)
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_OLDER:
                # click.echo("push newer content to remote : %s %s" % (doc.short_uid(), doc.name))
                status_code = yew.remote.push_doc(doc)
                if status_code == 200:
                    pdoc(doc, c, v)
                    #  click.secho('pushed successfully', fg='green')
                else:
                    click.secho(
                        "push failed: {}, {}".format(doc, status_code), fg="red"
                    )

                remote_done.append(doc.uid)
            elif c == Remote.STATUS_DOES_NOT_EXIST:
                #  click.echo("push new doc to remote       : %s %s" % (doc.short_uid(), doc.name))
                print(yew.remote.push_doc(doc))
                if r.status_code == 200:
                    #  click.secho('pushed successfully', fg='green')
                    pdoc(doc, c, v)
                else:
                    click.secho("pushed failed", fg="red")
                remote_done.append(doc.uid)
            elif c == Remote.STATUS_REMOTE_DELETED:
                # click.echo("remote was deleted           : %s %s" % (doc.short_uid(), doc.name))
                if prune:
                    yew.store.delete_document(doc)
                    #  click.secho("pruned local", fg='green')
                    pdoc(doc, c, v)
                else:
                    pdoc(doc, c, v)
            else:
                raise Exception("Invalid remote status   : %s for %s" % (c, str(doc)))
        except Exception as e:
            print(f"An error occured trying to sync {doc}")
            print(e)
    print("")

    # if we chose to update a single doc, we are done, no tag updates or anything else
    # because remote_done won't have values for the follow step to make sense
    if name:
        return

    remote_docs = yew.remote.get_docs()
    for rdoc in remote_docs:
        if rdoc["uid"] in remote_done:
            continue
        remote_doc = yew.remote.fetch(rdoc["uid"])
        click.echo(
            "importing doc: %s %s"
            % (remote_doc["uid"].split("-")[0], remote_doc["title"])
        )
        yew.store.import_document(
            remote_doc["uid"],
            remote_doc["title"],
            remote_doc["kind"],
            remote_doc["content"],
        )

    if False:
        r = yew.remote.push_tag_associations()
        if not r.status_code == 200:
            click.secho(r.text, fg="red")
        tags = yew.store.get_tags("")
        if len(tags) > 0:
            click.echo("syncing tags to server")
            tag_data = {}
            for tag in tags:
                tag_data[tag.tagid] = tag.name

            yew.remote.push_tags(tag_data)

        # get tags from server
        tags = yew.remote.pull_tags()
        if tags:
            click.echo("syncing tags from server")
            for tagid, name in tags.items():
                yew.store.sync_tag(tagid, name)

        tag_docs = yew.remote.pull_tag_associations()
        if tag_docs:
            click.echo("syncing tag associations")
            for tag_association in tag_docs:
                tid = tag_association["tid"]
                uid = tag_association["uid"]
                yew.store.associate_tag(uid, tid)
