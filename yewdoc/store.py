# -*- coding: utf-8 -*-
"""
Handle storing documents on the local disk. 

This module knows nothing about potential remote storage and syncing. 

When loaded, we read a json document that describes all available docs, the index.

The index can be generated from the document directory. 

"""

from typing import List, Optional, Dict
import codecs
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import traceback
import uuid

import click
import dateutil
import dateutil.parser

import pytz
import requests
import tzlocal
from requests.exceptions import ConnectionError
from strgen import StringGenerator as SG

import configparser

from .utils import (
    tar_directory,
    delete_directory,
    err,
    get_sha_digest,
    get_short_uid,
    is_binary_file,
    is_binary_string,
    is_short_uuid,
    is_uuid,
    modification_date,
    slugify,
    to_utc,
)

from .document import Document
from .tag import Tag, TagDoc
from . import file_system as fs
from .settings import Preferences


def read_document_index(user_directory) -> Dict:
    """Read document index into dict."""

    path = os.path.join(user_directory, "index.json")
    if not os.path.exists(path):
        return list()
    try:
        with open(path) as f:
            return json.load(f)
    except json.decoder.JSONDecodeError:
        print(f"Could not getting document index. Check file: {path}")


def match(frag, s):
    """Match a search string frag with string s.

    This is how we match document titles/names.

    """
    return re.search(frag, s, re.IGNORECASE)


def doc_from_data(store, data):
    return Document(store, data["uid"], data["title"], data["kind"])


def touch(path):
    """Update/create the access/modified time of the file at path."""
    with open(path, "a"):
        os.utime(path, None)


class YewStore(object):
    """Our data store.

    Handle storage of documents.

    """

    def __init__(self, username=None):
        """Init data required to find things on this local disk."""
        self.username = fs.get_username(username)
        self.yew_dir = fs.get_user_directory(self.username)
        self.prefs = Preferences(self.username)
        self.offline = False
        self.location = "default"
        self.index = read_document_index(self.yew_dir)

    def get_gnupg_exists(self):
        """Retro fit this."""
        fs.get_gnupg_exists()

    def get_counts(self):
        return len(self.index)

    def get_or_create_tag(self, name):
        """Create a new tag. Make sure it is unique."""

        return None

    def sync_tag(self, tagid, name):
        """Import a tag if not existing and return tag object."""

        return None

    def get_tag(self, tagid):
        """Get a tag by id."""
        return None

    def get_tags(self, name=None, exact=False):
        """Get all tags that match name and return a list of tag objects.

        If exact is True, the result will have at most one element.

        """
        return None

    def get_tag_associations(self):
        """Get tag associations."""
        return None

    def parse_tags(self, tag_string):
        """Parse tag_string and return a list of tag objects."""

        return None

    def associate_tag(self, uid, tagid):
        """Tag a document."""

        return None

    def dissociate_tag(self, tagid, uid):
        """Untag a document."""

        return None

    def delete_document(self, doc: Document) -> None:
        """Delete a document and its associated entities."""

        # remove files from local disk
        path = doc.directory_path
        # sanity check
        if not path.startswith(self.yew_dir):
            raise Exception("Path for deletion is wrong: %s" % path)
        if os.path.exists(path):
            shutil.rmtree(path)

        # remove from index
        self.index = list(filter(lambda d: d["uid"] != doc.uid, self.index))
        self.write_index()

    def change_doc_kind(self, doc, new_kind):
        """Change type of document.

        We just change the extension and update the index.

        """

        path_src = doc.path
        doc.kind = new_kind
        path_dest = doc.get_path()
        os.rename(path_src, path_dest)
        self.reindex_doc(doc)
        return doc

    def rename_doc(self, doc, new_name):
        """Rename document with name."""

        doc.name = new_name
        self.reindex_doc(doc)

        return doc

    def search_names(self, name_frag, exact=False, encrypted=False):
        """Get docs with LIKE unless matching exactly."""
        matching_docs = filter(lambda doc: match(name_frag, doc["title"]), self.index)
        docs = list()
        for data in matching_docs:
            docs.append(doc_from_data(self, data))
        return docs

    def get_doc(self, uid):
        """Get a doc or throw exception."""
        return doc_from_data(
            self, list(filter(lambda d: d["uid"] == uid, self.index))[0]
        )

    def write_index(self) -> None:
        """Write list of doc dicts."""
        path = os.path.join(self.yew_dir, "index.json")
        with open(path, "wt") as f:
            f.write(json.dumps(self.index, indent=4))

    def get_docs(self, tag_objects=[], encrypted=False) -> List[Document]:
        """Get all docs using the index.

        Does not get remote.

        """
        return [doc_from_data(self, data) for data in self.index]

    def verify_docs(self, prune=False) -> List:
        """Check that docs in the index exist on disk.
        Return uids of missing docs.
        Update the index if prune=True.
        """
        docs = self.get_docs()
        missing_uids = list()
        for doc in docs:
            if not os.path.exists(doc.path):
                print(f"Does not exist: {doc.uid} {doc.name}")
                missing_uids.append(doc.uid)
        if prune:
            self.index = list(
                filter(lambda d: d["uid"] not in missing_uids, self.index)
            )
            self.write_index()
        return missing_uids

    def generate_doc_data(self):
        """This generates the index data by reading
        the directory of files for the given user name.
        In case the index.json is corrupted or missing.
        """
        data = list()
        base_path = os.path.join(self.yew_dir, self.location)
        for uid_dir in os.scandir(base_path):
            path = os.path.join(base_path, uid_dir.name)
            for f in os.scandir(path):
                if f.is_file():
                    if not (
                        f.name.startswith(
                            (
                                "~",
                                "#",
                            )
                        )
                        or f.name.endswith(
                            (
                                "~",
                                "#",
                            )
                        )
                    ):
                        file_path = os.path.join(path, f.name)
                        with open(file_path, "rt") as fp:
                            digest = get_sha_digest(fp.read())
                        base, ext = os.path.splitext(f.name)
                        data.append(
                            {
                                "uid": uid_dir.name,
                                "title": base,
                                "kind": ext[1:],
                                "digest": digest,
                            }
                        )
                        break

        return data

    def generate_archive(self) -> str:
        """Create archive file in current directory of all docs."""
        archive_file_name = f"yew_{self.username}-{datetime.datetime.now().replace(microsecond=0).isoformat()}.tgz"
        tar_directory(self.yew_dir, archive_file_name)
        return archive_file_name

    def index_doc(self, uid, name, kind) -> Document:
        """Enter document into db for the first time.

        We assume the document exists in the directory not the index.
        But we handle the case where it is in the index.

        """
        try:
            doc = self.get_doc(uid)
            self.reindex_doc(doc)
        except Exception:
            # we expect to be here
            data = dict()
            data["uid"] = uid
            data["title"] = name
            data["kind"] = kind
            doc = doc_from_data(self, data)
            self.index.append(doc.serialize(no_content=True))
            self.write_index()

        return doc

    def reindex_doc(self, doc: Document) -> Document:
        """Refresh index information.

        The doc object has new information not yet in the index.
        """
        for d in self.index:
            if d.get("uid") == doc.uid:
                d["title"] = doc.name
                d["kind"] = doc.kind
                d["digest"] = doc.digest
                self.write_index()
                break

        return doc

    def get_short(self, s) -> Optional[Document]:
        """Get document but with abbreviated uid."""
        if not is_short_uuid(s):
            raise Exception("Not a valid short uid.")
        for d in self.index:
            if d.get("uid").startswith(s):
                return self.get_doc(d.get("uid"))
        return None

    def create_document(self, name, kind, content=None, symlink_source_path=None):
        """Create a new document.
        We might be using a symlink.
        """
        uid = str(uuid.uuid4())
        path = os.path.join(self.yew_dir, self.location, uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path, f"{name.replace(os.sep, '-')}.{kind.lower()}")

        if symlink_source_path:
            # we are symlinking to an existing path
            # we need an absolute path for this to work
            symlink_source_path = os.path.abspath(symlink_source_path)
            os.symlink(symlink_source_path, p)
        else:
            # the normal case
            touch(p)

        if os.path.exists(p):
            doc = self.index_doc(uid, name, kind)
            if content:
                doc.put_content(content)

        return self.get_doc(uid)

    def import_document(self, uid: str, name: str, kind: str, content: str) -> Document:
        """Create a document in storage using a string.
        We already know the uid.

        """
        path = os.path.join(self.yew_dir, self.location, uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path, f"{name.replace(os.sep, '-')}.{kind.lower()}")
        touch(p)
        if os.path.exists(p):
            self.index_doc(uid, name, kind)
        doc = self.get_doc(uid)
        doc.put_content(content)

        return doc
