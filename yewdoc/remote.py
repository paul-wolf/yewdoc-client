import os
import sys
import uuid
import traceback
from os.path import expanduser
import click
import sqlite3
import requests
from requests.exceptions import ConnectionError
from strgen import StringGenerator as SG
import json
import shutil
import hashlib
import codecs
import dateutil
import dateutil.parser
import datetime
import pytz
import tzlocal
import markdown
import difflib
import re

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
        self.token = u"Token %s" % self.store.get_user_pref('location.default.token')
        self.headers = {'Authorization': self.token, "Content-Type": "application/json"}
        self.url = self.store.get_user_pref('location.default.url')
        self.verify = False
        self.basic_auth_user = "yewser"
        self.basic_auth_pass = "yewleaf"
        self.basic_auth = False

        if not self.url:
            self.url = "https://doc.yew.io"
        
        # if store thinks we are offline
        self.offline = store.offline

    def check_data(self):
        if not self.token or not self.url:
            raise RemoteException("""Token and url required to reach server. Check user prefs.
            Try: 'yd configure'""")

    def get_headers(self):
        """Get headers used for remote calls."""
        return self.headers

    def get(self, endpoint, data={}, timeout=3):
        """Perform get on remote with endpoint."""
        self.check_data()
        url = u"%s/api/%s/" % (self.url, endpoint)
        return requests.get(url,
                            headers=self.headers,
                            params=data,
                            verify=self.verify,
                            timeout=timeout)

    def post(self, endpoint, data={}):
        """Perform post on remote."""
        url = u"%s/api/%s/" % (self.url, endpoint)
        return requests.post(url, headers=self.headers, data=json.dumps(data), verify=self.verify)

    def unauthenticated_post(self, endpoint, data={}):
        url = u"%s/%s/" % (self.url, endpoint)
        return requests.post(url, headers=self.headers, data=json.dumps(data), verify=self.verify)

    def delete(self, endpoint):
        """Perform delete on remote."""
        if self.offline:
            raise OfflineException()
        self.check_data()
        url = u"%s/api/%s/" % (self.url, endpoint)
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
            url = "%s/doc/register_user/" % self.url
            return requests.post(url, data=data, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def authenticate_user(self, data):
        """Authenticate a user that should exist on remote."""
        if self.offline:
            raise OfflineException()
        try:
            url = "{}/doc/authenticate_user/".format(self.url)
            return requests.post(url, data=data, verify=self.verify)
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def ping(self, timeout=3):
        """Call remote ping() method."""
        if self.offline:
            raise OfflineException()
        try:
            return self.get("ping", timeout=timeout)
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
            return self.get("")
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def doc_exists(self, uid):
        """Check if a remote doc with uid exists.

        Return remote digest or None.

        """
        if self.offline:
            raise OfflineException()
        r = self.get("exists", {"uid": uid})
        if r and r.status_code == 200:
            data = json.loads(r.content)
            if 'digest' in data:
                return data
        elif r and r.status_code == 404:
            return None
        return None

    def fetch(self, uid):
        """Get a document from remote.

        But just return a dictionary. Don't make it local.

        """
        if self.offline:
            raise OfflineException()
        try:
            r = self.get("document/%s" % uid)
            remote_doc = json.loads(r.content)
            return remote_doc
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    def get_docs(self):
        """Get list of remote documents."""
        if self.offline:
            raise OfflineException()
        r = self.get("document")
        try:
            response = json.loads(r.content)
            return response
        except ConnectionError:
            click.echo("Could not connect to server")
            return None

    STATUS_NO_CONNECTION = -1
    STATUS_REMOTE_SAME = 0
    STATUS_REMOTE_NEWER = 1
    STATUS_REMOTE_OLDER = 2
    STATUS_DOES_NOT_EXIST = 3
    STATUS_REMOTE_DELETED = 4

    STATUS_MSG = {
        STATUS_NO_CONNECTION: u"can't connect",
        STATUS_REMOTE_SAME: u"documents are the same",
        STATUS_REMOTE_NEWER: u"remote is newer",
        STATUS_REMOTE_OLDER: u"remote is older",
        STATUS_DOES_NOT_EXIST: u"remote does not exist",
        STATUS_REMOTE_DELETED: u"remote was deleted",
    }

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
            return Remote.STATUS_DOES_NOT_EXIST

        if 'deleted' in rexists:
            return Remote.STATUS_REMOTE_DELETED

        if rexists and rexists['digest'] == doc.get_digest():
            return Remote.STATUS_REMOTE_SAME

        remote_dt = dateutil.parser.parse(rexists['date_updated'])
        remote_newer = remote_dt > doc.get_last_updated_utc()
        if remote_newer:
            return Remote.STATUS_REMOTE_NEWER
        return Remote.STATUS_REMOTE_OLDER

    def pull_doc(self, uid):
        """Get document from server and store locally."""
        pass

    def remote_configured(self):
        token = self.store.get_user_pref('location.default.token')
        return True if token else False
    
    def push_doc(self, doc):
        """Serialize and send document.

        This will create the document on the server unless it exists.
        If it exists, it will be updated.

        """
        if self.offline:
            raise OfflineException()
        
        if not self.remote_configured():
            return Remote.STATUS_NO_CONNECTION
        
        try:
            status = self.doc_status(doc.uid)
        except RemoteException:
            click.echo("could not reach remote")
            return Remote.STATUS_NO_CONNECTION
        
        if status == Remote.STATUS_REMOTE_SAME \
           or status == Remote.STATUS_REMOTE_NEWER \
           or status == Remote.STATUS_REMOTE_DELETED:
            return status

        data = doc.serialize()

        if status == Remote.STATUS_REMOTE_OLDER:
            # it exists, so let's put together the update url and PUT it
            url = "%s/api/document/%s/" % (self.url, doc.uid)
            data = doc.serialize(no_uid=True)
            r = requests.put(url, data=data, headers=self.headers, verify=self.verify)
        elif status == Remote.STATUS_DOES_NOT_EXIST:
            # create a new one
            url = "%s/api/document/" % self.url
            r = requests.post(url, data=data, headers=self.headers, verify=self.verify)

            if not r.status_code == 200:
                print(r.content)

        return status


    def get_token(self, remote_username, password):
        """Get and store token for a registered user.

        username and password required

        """
        if self.offline:
            raise OfflineException()
        pass

    def push_tags(self, tag_data):
        """Post tags to server.


        """
        if self.offline:
            raise OfflineException()
        
        url = "%s/api/tag_list/" % (self.url)
        return requests.post(url, data=json.dumps(tag_data), headers=self.headers, verify=self.verify)

    def push_tag_associations(self):
        """Post tag associations to server.


        """
        if self.offline:
            raise OfflineException()

        tag_docs = self.store.get_tag_associations()   
        data = []
        for tag_doc in tag_docs:
            td = {}
            td['uid'] = tag_doc.uid
            td['tid'] = tag_doc.tagid
            data.append(td)
        url = "%s/api/tag_docs/" % (self.url)
        r = requests.post(url, data=json.dumps(data), headers=self.headers, verify=self.verify)
        return r


    def pull_tags(self):
        """Pull tags from server.

        """
        if self.offline:
            raise OfflineException()
        
        url = "%s/api/tag_list/" % (self.url)
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)

    
    def pull_tag_associations(self):
        """Pull tags from server.

        """
        if self.offline:
            raise OfflineException()
        
        url = "%s/api/tag_docs/" % (self.url)
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return json.loads(r.content)

