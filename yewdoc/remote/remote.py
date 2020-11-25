# -*- coding: utf-8 -*-
import sys
import json
import os
from typing import Optional, Dict, List

import click
import dateutil
import dateutil.parser
import requests
from requests.exceptions import ConnectionError

from .constants import RemoteStatus, STATUS_MSG
from .exceptions import OfflineException, RemoteException
from .. import utils

def pdoc(doc, status, verbose):
    """Print status to stdout."""

    if status == RemoteStatus.STATUS_REMOTE_SAME and not verbose:
        print(".", end="", flush=True)
    else:
        click.echo("", nl=True)
        click.echo(doc.name, nl=False)
        msg = STATUS_MSG[status]
        click.echo(": ", nl=False)
        click.secho(msg, fg="yellow")


def remote_doc_status(doc, remote_index) -> RemoteStatus:

    docs = list(filter(lambda d: d["uid"] == doc.uid, remote_index))
    if not docs:
        return RemoteStatus.STATUS_DOES_NOT_EXIST
    if doc.is_symlink:
        return RemoteStatus.STATUS_UNKNOWN  # we don't modify links during sync
    doc_remote = docs[0]
    doc_remote_updated = dateutil.parser.parse(doc_remote["date_updated"])
    if doc.digest == doc_remote["digest"]:
        return RemoteStatus.STATUS_REMOTE_SAME
    if doc.updated > doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_OLDER
    if doc.updated < doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_NEWER

    return RemoteStatus.STATUS_UNKNOWN

class Remote(object):
    """Handles comms with server."""

    def __init__(self, store):
        self.store = store
        self.store.digest_method = utils.get_sha_digest
        token = self.store.prefs.get_user_pref("location.default.token")
        self.token = f"Token {token}"
        self.headers = {"Authorization": self.token, "Content-Type": "application/json"}
        self.url = self.store.prefs.get_user_pref("location.default.url")
        self.verify = True
        self.basic_auth_user = "yewser"
        self.basic_auth_pass = "yewleaf"
        self.basic_auth = False

        if not self.url:
            self.url = "https://doc.yew.io"

        # if store thinks we are offline
        self.offline = store.offline

    @property
    def digest_method(self):
        """Return the digest method needed for our remote store."""
        return utils.get_sha_digest
    
    def check_data(self) -> None:
        """Raise exception if not configured properly else None."""
        if not self.token or not self.url:
            raise RemoteException(
                """Token and url required to reach server. Check user prefs.
            Try: 'yd configure'"""
            )

    def _get(self, endpoint, data={}, timeout=10) -> requests.Response:
        """Perform get on remote with endpoint."""
        self.check_data()
        url = f"{self.url}/api/{endpoint}/"
        return requests.get(
            url, headers=self.headers, params=data, verify=self.verify, timeout=timeout
        )

    def delete(self, uid) -> requests.Response:
        """Perform delete on remote.

        Seems to never be called.
        """

        self.check_data()
        url = f"{self.url}/api/delete/{uid}/"
        return requests.delete(url, headers=self.headers, verify=self.verify)


    def register_user(self, data) -> requests.Response:
        """Register a new user."""
        url = f"{self.url}/doc/register_user/"
        return requests.post(url, data=data, verify=self.verify)


    def authenticate_user(self, data) -> Optional[requests.Response]:
        """Authenticate a user that should exist on remote."""
        url = f"{self.url}/doc/authenticate_user/"
        return requests.post(url, data=data, verify=self.verify)


    def ping(self, timeout=3) -> Optional[requests.Response]:
        """Call remote ping() method."""
        try:
            return self._get("ping", timeout=timeout)
        except ConnectionError:
            click.echo("Could not connect to server")
            self.offline = True
            return None
        except Exception as e:
            click.echo(str(e))

    def unauthenticated_ping(self) -> Optional[requests.Response]:
        """Call remote ping() method."""
        try:
            url = "%s/doc/unauthenticated_ping/" % (self.url)
            return requests.get(url, headers=self.headers, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            self.offline = True
            return None
        except Exception as e:
            click.echo(str(e))
            return None

    def api(self) -> Optional[requests.Response]:
        """Return the api from remote."""
        if self.offline:
            raise OfflineException()
        try:
            return self._get("")
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def doc_exists(self, uid: str) -> Optional[Dict]:
        """Check if a remote doc with uid exists.

        Return remote digest or None.

        """
        r = self._get("exists", {"uid": uid})
        if r and r.status_code == 200:
            data = json.loads(r.content)
            if "digest" in data:
                return data
        elif r and r.status_code == 404:
            return None
        return None

    def fetch_doc(self, uid) -> Optional[Dict]:
        """Get a document from remote.

        But just return a dictionary. Don't make it local.
        The dict has the content.

        """
        try:
            r = self._get("document/%s" % uid)
            remote_doc = json.loads(r.content)
            return remote_doc
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def list_docs(self) -> Optional[List]:
        """Get list of remote documents."""
        if self.offline:
            raise OfflineException()
        r = self._get("document")
        try:
            return json.loads(r.content)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None
        except Exception as e:
            print(e)

    def doc_status(self, uid) -> RemoteStatus:
        """Return status: exists-same, exists-newer, exists-older, does-not-exist."""

        doc = self.store.get_doc(uid)

        # check if it exists on the remote server
        try:
            rexists = self.doc_exists(uid)
        except Exception as e:
            click.echo(e)
            return -1

        if not rexists:
            return RemoteStatus.STATUS_DOES_NOT_EXIST

        if "deleted" in rexists:
            return RemoteStatus.STATUS_REMOTE_DELETED

        if rexists and rexists["digest"] == doc.get_digest():
            return RemoteStatus.STATUS_REMOTE_SAME

        remote_dt = dateutil.parser.parse(rexists["date_updated"])
        remote_newer = remote_dt > doc.get_last_updated_utc()
        if remote_newer:
            return RemoteStatus.STATUS_REMOTE_NEWER
        return RemoteStatus.STATUS_REMOTE_OLDER


    def push_doc(self, doc) -> RemoteStatus:
        """Serialize and send document.

        This will create the document on the server unless it exists.
        If it exists, it will be updated.

        """
        self.check_data()

        try:
            status = self.doc_status(doc.uid)
        except RemoteException:
            click.echo("could not reach remote")
            return RemoteStatus.STATUS_NO_CONNECTION

        if (
            status == RemoteStatus.STATUS_REMOTE_SAME
            or status == RemoteStatus.STATUS_REMOTE_NEWER
            or status == RemoteStatus.STATUS_REMOTE_DELETED
        ):
            return status

        data = doc.serialize()

        if status == RemoteStatus.STATUS_REMOTE_OLDER:
            # it exists, so let's put together the update url and PUT it
            url = "%s/api/document/%s/" % (self.url, doc.uid)
            data = doc.serialize(no_uid=True)
            r = requests.put(url, json=data, headers=self.headers, verify=self.verify)
        elif status == RemoteStatus.STATUS_DOES_NOT_EXIST:
            # create a new one

            url = "%s/api/document/" % self.url
            r = requests.post(url, json=data, headers=self.headers, verify=self.verify)

            if not r.status_code == 200:
                print(r.content)

        return status

    def push_tags(self, tag_data) -> Optional[requests.Response]:
        """Post tags to server."""
        url = f"{self.url}/api/tag_list/"
        return requests.post(
            url, data=json.dumps(tag_data), headers=self.headers, verify=self.verify
        )

    def push_tag_associations(self) -> Optional[requests.Response]:
        """Post tag associations to server."""

        tag_docs = self.store.get_tag_associations()
        data = []
        for tag_doc in tag_docs:
            td = {}
            td["uid"] = tag_doc.uid
            td["tid"] = tag_doc.tagid
            data.append(td)
        url = f"{self.url}/api/tag_docs/"
        return requests.post(
            url, data=json.dumps(data), headers=self.headers, verify=self.verify
        )

    def pull_tags(self) -> List:
        """Pull tags from server."""

        url = f"{self.url}/api/tag_list/"
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)

    def pull_tag_associations(self) -> List:
        """Pull tags from server."""

        url = f"{self.url}/api/tag_docs/"
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)

    def sync(self, name, force, prune, verbose, fake, tags, list_docs):
        """Pushes local docs and pulls docs from remote.

        We don't overwrite newer docs.
        Does nothing if docs are the same.

        """

        v = verbose
        # make sure we are online
        try:
            r = self.ping()
        except Exception as e:
            click.echo(f"cannot connect: {e}")


        if name:
            docs_local = shared.get_document_selection(ctx, name, list_docs)
        else:
            docs_local = self.store.get_docs()
        remote_done = []
        deleted_index = self.store.get_deleted_index()
        remote_index = self.list_docs()

        for doc in docs_local:
            try:
                c = remote_doc_status(doc, remote_index)
                remote_done.append(doc.uid)
                if c == RemoteStatus.STATUS_REMOTE_SAME:
                    pdoc(doc, c, v)
                    continue
                elif c == RemoteStatus.STATUS_REMOTE_NEWER:
                    if not fake:
                        remote_doc = self.fetch_doc(doc.uid)
                        doc.put_content(remote_doc["content"])
                        if not remote_doc["title"] == doc.name:
                            self.store.rename_doc(doc, remote_doc["title"])
                    pdoc(doc, c, v)
                    remote_done.append(doc.uid)
                    continue
                elif c == RemoteStatus.STATUS_REMOTE_OLDER:
                    if not fake:
                        status_code = self.push_doc(doc)
                    else:
                        status_code = 200
                    if status_code == 200:
                        pdoc(doc, c, v)
                    else:
                        click.secho(f"push failed: {doc}, {status_code}", fg="red")

                    remote_done.append(doc.uid)
                    continue
                elif c == RemoteStatus.STATUS_DOES_NOT_EXIST:
                    if not fake:
                        status_code = self.push_doc(doc)
                    else:
                        status_code = 200
                    if r.status_code == 200:
                        pdoc(doc, c, v)
                    else:
                        click.secho("pushed failed", fg="red")
                    remote_done.append(doc.uid)
                elif c == RemoteStatus.STATUS_REMOTE_DELETED:
                    if prune:
                        if not fake:
                            self.store.delete_document(doc)
                        pdoc(doc, c, v)
                    else:
                        pdoc(doc, c, v)
                    continue
                elif c == RemoteStatus.STATUS_UNKNOWN:
                    # this happens for symlinks for instance
                    pdoc(doc, c, v)
                else:
                    raise Exception("Invalid remote status   : %s for %s" % (c, str(doc)))
            except Exception as e:
                print(f"An error occured trying to sync {doc}: {e}")
                traceback.print_exc()
        print("")

        # if we chose to update a single doc, we are done, no tag updates or anything else
        # because remote_done won't have values for the follow step to make sense
        if name:
            return

        for rdoc in remote_index:
            if rdoc["uid"] in remote_done:
                continue

            if not fake and rdoc["uid"] not in deleted_index:
                click.echo(f"importing doc: {rdoc['uid'].split('-')[0]} {rdoc['title']}")
                remote_doc = self.fetch_doc(rdoc["uid"])
                self.store.import_document(
                    remote_doc["uid"],
                    remote_doc["title"],
                    remote_doc["kind"],
                    remote_doc["content"],
                )

        # TODO: this all belongs in remote because it's specific to the REST remote
        # which has a different way of handling tags
        # and we are not pushing our tags
        if not tags:
            return 
        remote_tags = self.pull_tags()
        tag_docs = self.pull_tag_associations()
        print(f"Applying remote tags on local docs: {len(tag_docs)}")
        for tag_doc in tag_docs:
            tag_name = remote_tags[tag_doc["tid"]]
            doc = self.store.get_doc(tag_doc["uid"])
            # print(f"{tag_name} => {doc}")
            doc.add_tag(tag_name)
            self.store.reindex_doc(doc, write_index_flag=False)
        self.store.write_index()
