# -*- coding: utf-8 -*-
import sys
import json
import os
from typing import Optional, Dict, List
import datetime
import traceback

import click
import dateutil
import dateutil.parser
import requests
from requests.exceptions import ConnectionError
import s3fs

from .. import file_system as fs
from .constants import RemoteStatus, STATUS_MSG
from .exceptions import OfflineException, RemoteException
from .. import shared
from .. import utils

class RemoteS3Response:
    def __init__(self, status_code=200, content="ok"):
        self.status_code = status_code
        self.content = content
        
    def json(self):
        return json.loads(self.content)
        
    def __str__(self):
        return f"({self.status_code}) {self.content}"
        
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
        
def remote_doc_entry(uid, remote_index) -> Optional[Dict]:
    docs = list(filter(lambda d: d["uid"] == uid, remote_index))
    return docs[0] if docs else None

def remote_doc_status(doc_local, remote_index):
    doc_remote = remote_doc_entry(doc_local.uid, remote_index)
    if not doc_remote:
        return RemoteStatus.STATUS_DOES_NOT_EXIST
    doc_remote_updated = doc_remote["date_updated"]
    if doc_local.digest == doc_remote["digest"]:
        return RemoteStatus.STATUS_REMOTE_SAME
    elif doc_local.updated > doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_OLDER
    elif doc_local.updated < doc_remote_updated:
        return RemoteStatus.STATUS_REMOTE_NEWER

    return RemoteStatus.STATUS_UNKNOWN

class RemoteS3(object):
    """Handles comms with server."""

    def __init__(self, store):
        self.store = store
        self.store.digest_method = utils.get_md5_digest
        self.aws_access_key_id = store.prefs.get_user_pref("location.default.aws_access_key_id")
        self.aws_secret_access_key = store.prefs.get_user_pref("location.default.aws_secret_access_key")
        self.bucket = store.prefs.get_user_pref("location.default.s3_bucket")
        try:
            self.s3 = s3fs.S3FileSystem(key=self.aws_access_key_id, secret=self.aws_secret_access_key)
        except Exception as e:
            # this fails if we are here before credentials are completely setup
            print(e)

    @property
    def digest_method(self):
        """Return the digest method needed for our remote store."""
        return utils.get_md5_digest
    
    def check_data(self):
        if not self.bucket:
            raise RemoteException("s3_bucket user preference is required.")
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise RemoteException(
                "AWS credentials required to reach server. Check user prefs."
            )

    def remote_path(self, uid):
        """Rmote path. Only works if we have  local instance of doc."""
        doc = self.store.get_doc(uid)
        return f"{self.bucket}/{self.store.username}/{doc.uid}/{doc.filename}"
    
    def local_path(self, uid):
        """Local path. Only works if we have  local instance of doc."""        
        doc = self.store.get_doc(uid)
        return doc.path
        
    def delete(self, uid):
        """Perform delete on remote."""
        self.s3.delete(self.remote_path(uid))

    def register_user(self, data):
        """Register a new user."""
        raise NotImplementedError

    def authenticate_user(self, data):
        """Authenticate a user that should exist on remote."""
        raise NotImplementedError

    def ping(self, timeout=3) -> RemoteS3Response:
        """Call remote ping() method."""
        self.check_data()
        
        r = self.s3.ls(self.bucket)
        if len(r) == 0:
            # no docs yet
            r = datetime.datetime.now().isoformat()
        return RemoteS3Response(content=json.dumps(r))
            

    def unauthenticated_ping(self):
        """Call remote ping() method."""
        raise Exception("Cannot ping s3 without auth")

    def api(self) -> Dict:
        """Return the api from remote."""
        return {"remote": "s3"}

    def doc_exists(self, uid: str) -> Optional[str]:
        """Check if a remote doc with uid exists.

        Return remote digest or None.
        Requires local doc to exist.
        """
        remote_path = self.remote_path(uid)
        try:
            return self.s3.info(remote_path)
        except FileNotFoundError:
            print(f"Could not find document: {remote_path}")
            return None


    def fetch_doc(self, remote_index_entry: Dict) -> Optional[Dict]:
        """Get a document from remote.

        But just return a dictionary. Don't make it local.

        if we don't have the doc locally, we don't know what it's called. 
        we'll need to scan the remote directory. 

        """
        # import ipdb; ipdb.set_trace()
        uid = remote_index_entry["uid"]
        filename = f"{remote_index_entry['title']}.{remote_index_entry['kind']}"
        remote_path = f"{self.bucket}/{self.store.username}/{uid}/{filename}"        
        tmp_file = os.path.join(fs.get_tmp_directory(), remote_index_entry["uid"], filename)
        if not os.path.exists(os.path.join(fs.get_tmp_directory(), uid)):
            os.makedirs(os.path.join(fs.get_tmp_directory(), uid))
        self.s3.get_file(remote_path, tmp_file)
        with open(tmp_file, "rt") as f:
            remote_index_entry["content"] = f.read()
        return remote_index_entry

    def list_docs(self) -> Optional[List]:
        """Get list of remote documents."""
        # import ipdb; ipdb.set_trace()
        data = list()
        for f in self.s3.walk(f"{self.bucket}/{self.store.username}", detail=True):
            # f is a sequence of 3 elements; we want last element
            entry = f[2]
            if entry:
                for fn, file_info in entry.items():
                    if file_info["type"] == "file" and not fn.startswith("__"):
                        base, ext = os.path.splitext(fn)
                        data.append(
                            {
                                "uid": file_info["name"].split("/")[-2],
                                "title": base,
                                "kind": ext[1:],
                                "digest": json.loads(file_info["ETag"]),
                                "date_updated": file_info["LastModified"],
                                "tags": list(),
                            }
                        )

        return data


    def push_doc(self, doc, force=False) -> None:
        """Serialize and send document.

        This will create the document on the server unless it exists.
        If it exists, it will be updated.

        """
        self.check_data()
        data = doc.serialize()
        self.s3.put(self.local_path(doc.uid), self.remote_path(doc.uid))            


    def push_tags(self, tag_data):
        """Post tags to server."""
        self.s3.put()


    def pull_tags(self):
        """Pull tags from server."""
        self.s3.get()

    def sync(self, name, force, prune, verbose, fake, tags, list_docs):
        """Pushes local docs and pulls docs from remote.

        We don't overwrite newer docs.
        Does nothing if docs are the same.

        """

        v = verbose
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
        # print(json.dumps(remote_index, indent=4, default=str))
        for doc in docs_local:
            try:
                c = remote_doc_status(doc, remote_index)
                remote_done.append(doc.uid)
                if c == RemoteStatus.STATUS_REMOTE_SAME:
                    pdoc(doc, c, v)
                    continue
                elif c == RemoteStatus.STATUS_REMOTE_NEWER:
                    if not fake:
                        remote_doc_data = remote_doc_entry(doc.uid, remote_index)
                        remote_doc = self.fetch_doc(remote_doc_data)
                        doc.put_content(remote_doc["content"])
                        if not remote_doc["title"] == doc.name:
                            self.store.rename_doc(doc, remote_doc["title"])
                    pdoc(doc, c, v)
                    remote_done.append(doc.uid)
                    continue
                elif c == RemoteStatus.STATUS_REMOTE_OLDER:
                    if not fake:
                        try:
                            self.push_doc(doc)
                            pdoc(doc, c, v)                            
                        except Exception as e:
                            click.secho(f"push failed: {doc}, {e}", fg="red")                            
                    remote_done.append(doc.uid)
                    continue
                elif c == RemoteStatus.STATUS_DOES_NOT_EXIST:
                    if not fake:
                        try:
                            self.push_doc(doc)
                            pdoc(doc, c, v)                            
                        except Exception as e:
                            click.secho(f"push failed: {doc}, {e}", fg="red")                            
                    remote_done.append(doc.uid)
                    continue
                elif c == RemoteStatus.STATUS_REMOTE_DELETED:
                    if prune:
                        if not fake:
                            self.store.delete_document(doc)
                    pdoc(doc, c, v)
                    continue
                elif c == RemoteStatus.STATUS_UNKNOWN:
                    # this happens for symlinks for instance
                    pdoc(doc, c, v)
                else:
                    raise Exception(f"Invalid remote status: {c} for {doc}")
            except Exception as e:
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
        


