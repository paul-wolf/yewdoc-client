# -*- coding: utf-8 -*-
from typing import List, Optional, Dict
import codecs
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
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
    bcolors,
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

from . document import Document
from . tag import Tag, TagDoc
from . import file_system as fs
from . settings import Preferences

class YewStore(object):
    """Our data store.

    Handle storage of documents.

    """

    def __init__(self, username=None):
        """Init data required to find things on this local disk."""

        self.yew_dir = fs.get_user_directory(fs.get_username(username))
        self.yewdb_path = os.path.join(self.yew_dir, "yew.db")
        self.conn = self.make_db(self.yewdb_path)
        self.username = fs.get_username(username)
        self.prefs = Preferences(self.username)
        self.offline = False
        self.location = "default"

    def get_gnupg_exists(self):
        """Retro fit this."""
        fs.get_gnupg_exists()
        
    def make_db(self, path):
        """Create the db if not exist and get or create tables."""
        conn = sqlite3.connect(path)
        c = conn.cursor()


        sql = """CREATE TABLE IF NOT EXISTS document (
           uid NOT NULL,
           name NOT NULL,
           location NOT NULL,
           kind NOT NULL,
           digest,
           folderid,
           FOREIGN KEY(folderid) REFERENCES folder(folderid)
        );"""
        c.execute(sql)

        try:
            sql = """
            ALTER TABLE Document ADD COLUMN encrypt INTEGER
            """
            c.execute(sql)
        except Exception:
            # if it is already added
            #  print(e)
            pass

        sql = """CREATE TABLE IF NOT EXISTS folder (
           folderid,
           parentid ,
           name NOT NULL,
           FOREIGN KEY(parentid) REFERENCES folder(folderid)
        );"""
        c.execute(sql)

        sql = """
        CREATE TABLE IF NOT EXISTS tag (
            location NOT NULL,
            tagid NOT NULL,
            name NOT NULL,
            PRIMARY KEY (location, tagid),
            UNIQUE(location,name)
        );"""
        c.execute(sql)

        sql = """CREATE TABLE IF NOT EXISTS tagdoc (
            uid NOT NULL,
            tagid NOT NULL,
            FOREIGN KEY(uid) REFERENCES document(uid),
            FOREIGN KEY(tagid) REFERENCES document(tagid),
            UNIQUE(uid,tagid)
        );"""
        c.execute(sql)

        conn.commit()
        return conn

    def get_counts(self):
        data = {}

        c = self.conn.cursor()
        c.execute("SELECT count(*) FROM document;")
        row = c.fetchone()
        data["documents"] = row[0]

        c.execute("SELECT count(*) FROM tag;")
        row = c.fetchone()
        data["tags"] = row[0]

        return data

    def get_or_create_tag(self, name):
        """Create a new tag. Make sure it is unique."""

        c = self.conn.cursor()
        tagid = SG(r"#[\l\d]{8}").render()
        s = "INSERT OR IGNORE INTO tag VALUES (?,?,?);"
        # print "INSERT OR IGNORE INTO tag VALUES ('%s','%s','%s')" % (self.location,tagid,name)
        c.execute(s, (self.location, tagid, name))
        self.conn.commit()
        s = "SELECT * FROM tag WHERE tagid = ?"
        c.execute(s, (tagid,))
        row = c.fetchone()
        tag = Tag(store=self, location=row[0], tagid=row[1], name=row[2])
        return tag

    def sync_tag(self, tagid, name):
        """Import a tag if not existing and return tag object."""

        c = self.conn.cursor()
        s = "INSERT OR IGNORE INTO tag VALUES (?,?,?);"
        # print "INSERT OR IGNORE INTO tag VALUES ('%s','%s','%s')" % (self.location,tagid,name)
        c.execute(s, (self.location, tagid, name))
        self.conn.commit()
        s = "SELECT * FROM tag WHERE tagid = ?"
        c.execute(s, (tagid,))
        row = c.fetchone()
        if not row:
            return None
        tag = Tag(store=self, location=row[0], tagid=row[1], name=row[2])
        return tag

    def get_tag(self, tagid):
        """Get a tag by id."""
        tag = None
        c = self.conn.cursor()
        s = "SELECT * FROM tag WHERE location = ? AND tagid = ?"
        c.execute(s, (self.location, tagid))
        row = c.fetchone()
        if row:
            tag = Tag(store=self, location=row[0], tagid=row[1], name=row[2])
        return tag

    def get_tags(self, name=None, exact=False):
        """Get all tags that match name and return a list of tag objects.

        If exact is True, the result will have at most one element.

        """
        tags = []
        c = self.conn.cursor()
        if not name:
            s = "SELECT * FROM tag WHERE location = ?"
            c.execute(s, (self.location,))
        elif exact:
            s = "SELECT * FROM tag WHERE location = ? AND name = ?"
            c.execute(s, (self.location, name))
        else:
            s = "SELECT * FROM tag WHERE location = ? AND name LIKE ?"
            c.execute(s, (self.location, name + "%"))
        rows = c.fetchall()
        for row in rows:
            tag = Tag(store=self, location=row[0], tagid=row[1], name=row[2])
            tags.append(tag)
        return tags

    def get_tag_associations(self):
        """Get tag associations."""
        c = self.conn.cursor()
        s = "SELECT * FROM tagdoc"
        c.execute(s)
        tag_docs = []
        rows = c.fetchall()
        for row in rows:
            tag_docs.append(TagDoc(store=self, tagid=row[1], uid=row[0]))
        return tag_docs

    def parse_tags(self, tag_string):
        """Parse tag_string and return a list of tag objects."""

        string_tags = tag_string.split(",")
        tag_list = []
        for t in string_tags:
            tags = self.get_tags(t, exact=True)
            if len(tags) > 0:
                tag_list.append(tags[0])
        return tag_list

    def associate_tag(self, uid, tagid):
        """Tag a document."""

        c = self.conn.cursor()
        s = "INSERT OR IGNORE INTO tagdoc VALUES (?,?)"
        c.execute(s, (uid, tagid))
        self.conn.commit()

    def dissociate_tag(self, tagid, uid):
        """Untag a document."""

        c = self.conn.cursor()
        s = "DELETE FROM tagdoc WHERE tagid = ? and uid = ?"
        c.execute(s, (uid, tagid))
        self.conn.commit()

    def delete_document(self, doc):
        """Delete a document and its associated entities."""

        # remove record
        c = self.conn.cursor()
        sql = "DELETE FROM document WHERE uid = ?"
        c.execute(sql, (doc.uid,))

        # remove files
        path = doc.directory_path
        # sanity check
        if not path.startswith(get_storage_directory()):
            raise Exception("Path for deletion is wrong: %s" % path)
        shutil.rmtree(path)

        self.conn.commit()


    def get_doc(self, uid):
        """Get a doc or None."""

        doc = None
        sql = "select uid,name,location,kind,encrypt,ipfs_hash FROM document WHERE uid = ?"
        c = self.conn.cursor()
        c.execute(sql, (uid,))
        row = c.fetchone()
        if row:
            doc = Document(
                store=self,
                uid=row[0],
                name=row[1],
                location=row[2],
                kind=row[3],
                encrypt=row[4],
                ipfs_hash=row[5],
            )
        c.close()
        return doc

    def change_doc_kind(self, doc, new_kind):
        """Change type of document."""

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

        c = self.conn.cursor()

        if not exact:
            sql = "SELECT uid,name,location,kind,encrypt,ipfs_hash FROM document WHERE name LIKE ?"
            if encrypted:
                sql += " AND encrypt is true"
            c.execute(sql, ("%" + name_frag + "%",))
        else:
            sql = "SELECT uid,name,location,kind,encrypt,ipfs_hash FROM document WHERE name = ?"
            if encrypted:
                sql += " AND encrypt is true"
            c.execute(sql, (name_frag,))

        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self, row[0], row[1], row[2], row[3], row[4], row[5]))
        c.close()
        return docs

    def get_docs(self, tag_objects=[], encrypted=False) -> List[Document]:
        """Get all docs using the index.

        Does not get remote.

        tags is a list of tagid's. These must have been
        put together correctly before passing them here.

        """
        where_tags = ""
        if tag_objects:
            tags = ",".join(["'" + tag.tagid + "'" for tag in tag_objects])
            where_tags = (
                " WHERE uid IN (SELECT uid FROM tagdoc WHERE tagid IN (%s))" % tags
            )
        sql = "SELECT uid, name, location, kind, encrypt, ipfs_hash FROM document "
        if where_tags:
            sql += where_tags
        if encrypted:
            if where_tags:
                sql += " AND "
            else:
                sql += " WHERE "
            sql += " encrypt is true"
        c = self.conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self, row[0], row[1], row[2], row[3], row[4], row[5]))
        c.close()
        return docs

    def index_doc(self, uid, name, location, kind):
        """Enter document into db for the first time.

        TODO: check if exists.

        """

        if not location:
            location = "default"
        # check if present
        uid_name = self.get_doc(uid)
        if not uid_name:
            # then put into index
            c = self.conn.cursor()
            sql = "INSERT INTO document (uid, name, location,kind) VALUES (?,?,?,?)"
            c.execute(sql, (uid, name, location, kind))
            self.conn.commit()
            c.close()
        return self.get_doc(uid)

    def reindex_doc(self, doc):
        """Refresh index information."""

        # check if present
        # if not self.get_doc(doc.uid):
        #    raise Exception("Can't reindex non-existant document.")
        c = self.conn.cursor()
        sql = "UPDATE document SET name=?, location=?, kind=?, digest=? WHERE uid = ?"
        c.execute(sql, (doc.name, doc.location, doc.kind, doc.digest, doc.uid))
        self.conn.commit()
        c.close()
        return doc

    def get(self, uid):
        """Get a single document with the uid from local store."""

        if not is_uuid(uid):
            raise Exception("Not a valid uid.")

        sql = "SELECT uid,name,location,kind,encrypt,ipfs_hash FROM document WHERE uid = ?"
        c = self.conn.cursor()
        c.execute(sql, (uid,))
        row = c.fetchone()
        if not row:
            return None
        return Document(self, row[0], row[1], row[2], row[3], row[4], row[5])

    def get_short(self, s):
        """Get document but with abbreviated uid."""
        if not is_short_uuid(s):
            raise Exception("Not a valid short uid.")
        sql = "select uid FROM document WHERE uid LIKE ?"
        c = self.conn.cursor()
        c.execute(sql, (s + "%",))
        row = c.fetchone()
        if not row:
            return None
        return self.get(row[0])  # should be full uid

    def touch(self, path):
        with codecs.open(path, "a", "utf-8"):
            os.utime(path, None)

    def create_document(
        self, name, location, kind, content=None, symlink_source_path=None
    ):
        if not location:
            location = self.location
        uid = str(uuid.uuid1())
        path = os.path.join(self.yew_dir, location or self.location, uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path, "doc." + kind.lower())

        if symlink_source_path:
            # we are symlinking to an existing path
            # we need an absolute path for this to work
            symlink_source_path = os.path.abspath(symlink_source_path)
            os.symlink(symlink_source_path, p)
        else:
            # the normal case
            self.touch(p)

        if os.path.exists(p):
            doc = self.index_doc(uid, name, location, kind)
            if content:
                doc.put_content(content)

        doc.toggle_encrypted()
        return self.get_doc(uid)

    def import_document(self, uid, name, location, kind, content):
        if not location:
            location = self.location
        path = os.path.join(fs.get_storage_directory(), location, uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path, "doc." + kind.lower())
        self.touch(p)
        if os.path.exists(p):
            self.index_doc(uid, name, location, kind)
        doc = self.get_doc(uid)
        doc.put_content(content)
        doc.toggle_encrypted()
        return doc
