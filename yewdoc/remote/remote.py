# -*- coding: utf-8 -*-
import sys
import json
import os
from typing import Optional

import click
import dateutil
import dateutil.parser
import requests
from requests.exceptions import ConnectionError

from .constants import RemoteStatus, STATUS_MSG


class RemoteException(Exception):
    """Custom exception for remote errors."""

    pass


class OfflineException(Exception):
    """Raised if remote operation attempted when offline."""

    pass


class Remote(object):
    """Handles comms with server."""

    def __init__(self, store):
        self.store = store
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

    def check_data(self):
        if not self.token or not self.url:
            raise RemoteException(
                """Token and url required to reach server. Check user prefs.
            Try: 'yd configure'"""
            )

    def _get(self, endpoint, data={}, timeout=10):
        """Perform get on remote with endpoint."""
        self.check_data()
        url = f"{self.url}/api/{endpoint}/"
        return requests.get(
            url, headers=self.headers, params=data, verify=self.verify, timeout=timeout
        )

    def unauthenticated_post(self, endpoint, data={}):
        url = f"{self.url}/{endpoint}/"
        return requests.post(
            url, headers=self.headers, data=json.dumps(data), verify=self.verify
        )

    def delete(self, endpoint):
        """Perform delete on remote."""
        if self.offline:
            raise OfflineException()
        self.check_data()
        url = f"{self.url}/api/{endpoint}/"
        try:
            return requests.delete(url, headers=self.headers, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def register_user(self, data):
        """Register a new user."""
        if self.offline:
            raise OfflineException()
        try:
            url = f"{self.url}/doc/register_user/"
            return requests.post(url, data=data, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def authenticate_user(self, data):
        """Authenticate a user that should exist on remote."""
        if self.offline:
            raise OfflineException()
        try:
            url = f"{self.url}/doc/authenticate_user/"
            return requests.post(url, data=data, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def ping(self, timeout=3):
        """Call remote ping() method."""
        if self.offline:
            raise OfflineException()
        try:
            return self._get("ping", timeout=timeout)
        except ConnectionError:
            click.echo("Could not connect to server")
            self.offline = True
            return None
        except Exception as e:
            click.echo(str(e))

    def unauthenticated_ping(self):
        """Call remote ping() method."""
        if self.offline:
            raise OfflineException()
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

    def api(self):
        """Return the api from remote."""
        if self.offline:
            raise OfflineException()
        try:
            return self._get("")
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def doc_exists(self, uid: str) -> Optional[str]:
        """Check if a remote doc with uid exists.

        Return remote digest or None.

        """
        if self.offline:
            raise OfflineException()
        r = self._get("exists", {"uid": uid})
        if r and r.status_code == 200:
            data = json.loads(r.content)
            if "digest" in data:
                return data
        elif r and r.status_code == 404:
            return None
        return None

    def fetch_doc(self, uid):
        """Get a document from remote.

        But just return a dictionary. Don't make it local.

        """
        if self.offline:
            raise OfflineException()
        try:
            r = self._get("document/%s" % uid)
            remote_doc = json.loads(r.content)
            return remote_doc
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def list_docs(self):
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

    def doc_status(self, uid):
        """Return status: exists-same, exists-newer, exists-older, does-not-exist."""

        if self.offline:
            raise OfflineException()

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

    def remote_configured(self) -> bool:
        token = self.store.prefs.get_user_pref("location.default.token")
        return True if token else False

    def push_doc(self, doc):
        """Serialize and send document.

        This will create the document on the server unless it exists.
        If it exists, it will be updated.

        """
        if self.offline:
            raise OfflineException()

        if not self.remote_configured():
            return RemoteStatus.STATUS_NO_CONNECTION

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

    def push_tags(self, tag_data):
        """Post tags to server."""
        if self.offline:
            raise OfflineException()

        url = f"{self.url}/api/tag_list/"
        return requests.post(
            url, data=json.dumps(tag_data), headers=self.headers, verify=self.verify
        )

    def push_tag_associations(self):
        """Post tag associations to server."""
        if self.offline:
            raise OfflineException()

        tag_docs = self.store.get_tag_associations()
        data = []
        for tag_doc in tag_docs:
            td = {}
            td["uid"] = tag_doc.uid
            td["tid"] = tag_doc.tagid
            data.append(td)
        url = f"{self.url}/api/tag_docs/"
        r = requests.post(
            url, data=json.dumps(data), headers=self.headers, verify=self.verify
        )
        return r

    def pull_tags(self):
        """Pull tags from server."""
        if self.offline:
            raise OfflineException()

        url = f"{self.url}/api/tag_list/"
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)

    def pull_tag_associations(self):
        """Pull tags from server."""
        if self.offline:
            raise OfflineException()

        url = f"{self.url}/api/tag_docs/"
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)
