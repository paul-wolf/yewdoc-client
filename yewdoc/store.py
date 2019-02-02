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
import configparser
 
from . utils import (bcolors, is_binary_file, is_binary_string, slugify,
                                          err, is_uuid, is_short_uuid, get_short_uid,
                                          delete_directory, get_sha_digest, to_utc,
                                          modification_date)

class Tag(object):

    def __init__(self, store, location, tagid, name):
        self.store = store
        self.location = location
        self.tagid = tagid
        self.name = name

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.name


class TagDoc(object):

    def __init__(self, store, tagid, uid):
        self.store = store
        self.tagid = tagid
        self.uid = uid


class Document(object):
    """Describes a document."""

    def __init__(self, store, uid, name, location, kind):
        self.store = store
        self.uid = uid
        self.name = name
        self.location = location
        self.kind = kind
        self.path = os.path.join(store.get_storage_directory(), location, uid, u"doc." + kind)
        # TODO: lazy load
        self.digest = self.get_digest()
        self.directory_path = os.path.join(store.get_storage_directory(), location, uid)

    def short_uid(self):
        """Return first part of uuid."""
        return self.uid.split('-')[0]

    def get_safe_name(self):
        """Return safe name."""
        return slugify(self.name)

    def get_digest(self):
        return get_sha_digest(self.get_content())

    def get_basename(self):
        return 'doc'

    def get_filename(self):
        return u"%s.%s" % (self.get_basename(), self.kind)

    def get_path(self):
        return os.path.join(self.store.get_storage_directory(), self.location, self.uid,
                            self.get_filename())
    def is_link(self):
        return os.path.islink(self.get_path())

    def get_media_path(self):
        path = os.path.join(self.store.get_storage_directory(), self.location, self.uid,
                            'media')
        if not os.path.exists(path):
            os.makedirs(path)
            #os.chmod(path, 0x776)
        return path

    def validate(self):
        if not os.path.exists(self.get_path()):
            raise Exception("Non-existant document: %s" % self.path)
        # should also check that we are in sync with index
        return True

    def dump(self):
        click.echo("uid      : %s" % self.uid)
        click.echo("link     : %s" % self.is_link())
        click.echo("title    : %s" % self.name)
        click.echo("location : %s" % self.location)
        click.echo("kind     : %s" % self.kind)
        click.echo("size     : %s" % self.get_size())
        click.echo("digest   : %s" % self.digest)
        click.echo("path     : %s" % self.path)
        click.echo("Last modified: %s" % modification_date(self.get_path()))

    def get_last_updated_utc(self):
        return modification_date(self.get_path())

    def get_size(self):
        return os.path.getsize(self.get_path())

        return len(self.get_content())

    def serialize(self, no_uid=False):
        """Serialize as json to send to server."""
        data = {}
        data['uid'] = self.uid
        data['parent'] = None
        data['title'] = self.name
        data['kind'] = self.kind
        data['content'] = self.get_content()  # open(self.get_path()).read()
        data['digest'] = self.digest
        return json.dumps(data)

    def get_content(self):
        """Get the content."""
        f = codecs.open(self.path, "r", "utf-8")
        s = f.read()
        f.close()
        return s

    def put_content(self, content, mode='w'):
        f = codecs.open(self.path, mode, "utf-8")
        return f.write(content)

    def __str__(self):
        return str(self.__unicode__())

    def __unicode__(self):
        return self.name


class YewStore(object):
    """Our data store.

    Persistent user and project preferences.

    """

    yewdb_path = None
    conn = None
    username = None
    
    global_preferences = [
        "username",
        "offline",
    ]

    # mainly preferences required to connect to server
    user_preferences = [
        "location.default.url",
        "location.default.email",
        "location.default.username",
        "location.default.password",
        "location.default.first_name",
        "location.default.last_name",
        "location.default.token",
        #"default_doc_type",
        #"current_doc",
    ]

    doc_kinds = [
        "md",
        "txt",
        "rst",
        "json",
    ]

    DEFAULT_USERNAME = 'yewser'

    def get_username(self, username=None):
        """Return username.

        Try to get a username that determines the repo of docs.

        Try to get it 
           from the caller.
           from the environment
           from a properties file ~/.yew
           user the default constant 'yewser'

        """
        
        home = expanduser("~")
        file_path = os.path.join(home, '.yew')

        if username:
            return username
        elif os.getenv('YEWDOC_USER'):
            username = os.getenv('YEWDOC_USER')
        elif os.path.exists(file_path):
            config = configparser.ConfigParser()     
            with open(file_path, 'r') as f:
               s = f.read()
               config.read_string(s)
            try:
                username = config['Yewdoc']['username']
            except Exception as e:
               pass
           
        return username if username else YewStore.DEFAULT_USERNAME
    
    def get_user_directory(self):
        """Get the directory for the current local user.

        Expand home and then find current yewdocs user.

        If username is not None, use that as user name.

        """
        home = expanduser("~")
        yew_dir = os.path.join(home, '.yew.d', self.username)
        if not os.path.exists(yew_dir):
            os.makedirs(yew_dir)
        return yew_dir

    def __init__(self, username=None):
        """Make sure storage is setup."""

        self.username = self.get_username(username)
        yew_dir = self.get_user_directory()
        self.yewdb_path = os.path.join(yew_dir, 'yew.db')
        self.conn = self.make_db(self.yewdb_path)
        # TODO: change this to be the same as get_user_directory()
        self.username = self.get_global('username', self.username)
        self.offline = self.get_global('offline', False)
        self.location = 'default'

    def get_storage_directory(self):
        """Return path for storage."""
        return self.get_user_directory()

    def get_tmp_directory(self):
        """Return path for temporary storage."""

        tmp_dir = os.path.join(self.get_storage_directory(), 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        return tmp_dir

    def make_db(self, path):
        """Create the db if not exist and get or create tables."""
        conn = sqlite3.connect(path)
        c = conn.cursor()
        sql = '''
        CREATE TABLE IF NOT EXISTS global_prefs (
           key NOT NULL,
           value NOT NULL
        );
        '''
        c.execute(sql)

        sql = '''CREATE TABLE IF NOT EXISTS user_prefs (
           username NOT NULL,
           key NOT NULL,
           value NOT NULL
        );'''
        c.execute(sql)

        sql = '''CREATE TABLE IF NOT EXISTS user_project_prefs (
           username NOT NULL,
           project NOT NULL,
           key NOT NULL,
           value NOT NULL
        );'''
        c.execute(sql)

        sql = '''CREATE TABLE IF NOT EXISTS document (
           uid NOT NULL,
           name NOT NULL,
           location NOT NULL,
           kind NOT NULL,
           digest,
           folderid,
           FOREIGN KEY(folderid) REFERENCES folder(folderid)
        );'''
        c.execute(sql)

        sql = '''CREATE TABLE IF NOT EXISTS folder (
           folderid,
           parentid ,
           name NOT NULL,
           FOREIGN KEY(parentid) REFERENCES folder(folderid)
        );'''
        c.execute(sql)

        sql = '''
        CREATE TABLE IF NOT EXISTS tag (
            location NOT NULL,
            tagid NOT NULL,
            name NOT NULL,
            PRIMARY KEY (location, tagid),
            UNIQUE(location,name)
        );'''
        c.execute(sql)

        sql = '''CREATE TABLE IF NOT EXISTS tagdoc (
            uid NOT NULL,
            tagid NOT NULL,
            FOREIGN KEY(uid) REFERENCES document(uid),
            FOREIGN KEY(tagid) REFERENCES document(tagid),
            UNIQUE(uid,tagid)
        );'''
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
        tagid = SG("#[\l\d]{8}").render()
        s = "INSERT OR IGNORE INTO tag VALUES (?,?,?);"
        # print "INSERT OR IGNORE INTO tag VALUES ('%s','%s','%s')" % (self.location,tagid,name)
        c.execute(s, (self.location, tagid, name))
        self.conn.commit()
        s = "SELECT * FROM tag WHERE tagid = ?"
        c.execute(s, (tagid,))
        row = c.fetchone()
        tag = Tag(
            store=self,
            location=row[0],
            tagid=row[1],
            name=row[2]
        )
        return tag
    
    def sync_tag(self, tagid, name):
        """Import a tag if not existing and return tag object.
        """

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
        tag = Tag(
            store=self,
            location=row[0],
            tagid=row[1],
            name=row[2]
        )
        return tag

    def get_tag(self, tagid):
        """Get a tag by id.
        """
        tag = None
        c = self.conn.cursor()
        s = "SELECT * FROM tag WHERE location = ? AND tagid = ?"
        c.execute(s, (self.location,tagid))
        row = c.fetchone()
        if row:
            tag = Tag(
                store=self,
                location=row[0],
                tagid=row[1],
                name=row[2]
            )
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
            tag = Tag(
                store=self,
                location=row[0],
                tagid=row[1],
                name=row[2]
            )
            tags.append(tag)
        return tags

    def get_tag_associations(self):
        """Get tag associations.

        """
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

        string_tags = tag_string.split(',')
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
        if not path.startswith(self.get_storage_directory()):
            raise Exception("Path for deletion is wrong: %s" % path)
        shutil.rmtree(path)

        self.conn.commit()

    def update_recent(self, username, doc):
        """Update most recent list.

        Return list of uids.

        """

        list_unparsed = self.get_user_pref("recent_list")
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
        else:
            list_parsed = []
        if doc.uid in list_parsed:
            list_parsed.remove(doc.uid)  # take it out
        list_parsed.insert(0, doc.uid)  # make it the first one
        # now save the new list
        self.put_user_pref('recent_list', json.dumps(list_parsed))

    def get_recent(self, username):
        """Get most recent documents."""

        list_unparsed = self.get_user_pref("recent_list")
        docs = []
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
            for uid in list_parsed:
                d = self.get_doc(uid)
                if d:
                    docs.append(d)
            return docs
        return []

    def get_global(self, k, default=None):
        # print "get_global (key): ", k
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM global_prefs WHERE key = ?"
        c.execute(sql, (k,))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
        if not v and default:
            return default
        return v

    def get_globals(self):
        """Get all global prefs."""
        c = self.conn.cursor()
        sql = "SELECT key,value FROM global_prefs"
        c.execute(sql)
        rows = c.fetchall()
        c.close()
        return rows

    def put_global(self, k, v):
        """Set a global preference. Must be in class var global_preferences."""

        if not k in YewStore.global_preferences:
            raise ValueError("Unknown global preference: %s. Choices are: %s" %
                             (k, ", ".join(YewStore.global_preferences)))
        # print "put_global (%s,%s)" % (k,v)
        if not k or not v:
            print("not storing nulls")
            return  # don't store null values
        c = self.conn.cursor()
        if self.get_global(k):
            sql = "UPDATE global_prefs SET value = ? WHERE key = ?"
            # print "UPDATE global_prefs SET value = '%s' WHERE key = '%s'" % (v,k)
            c.execute(sql, (v, k,))
            click.echo("updated global: %s = %s" % (k, self.get_global(k)))
        else:
            sql = "INSERT INTO global_prefs VALUES (?,?)"
            c.execute(sql, (k, v,))
            click.echo("created global: %s = %s" % (k, self.get_global(k)))

        self.conn.commit()
        c.close()

    def get_user_pref(self, k):
        # print "get_user_pref (%s,%s): " % (username,k)
        username = self.username
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM user_prefs WHERE username = ? AND key = ?"
        c.execute(sql, (username, k))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
        return v

    def put_user_pref(self, k, v):
        username = self.username
        # print "put_user_pref (%s,%s,%s): "% (username,k,v)
        if not k or not v:
            click.echo("not storing nulls")
            return  # don't store null values
        c = self.conn.cursor()
        if self.get_user_pref(k):
            sql = "UPDATE user_prefs SET value = ? WHERE username = ? AND key = ?"
            # print "UPDATE user_prefs SET value = %s WHERE username = %s AND key = %s" % (v,username,k)
            c.execute(sql, (v, username, k))
            self.conn.commit()
        else:
            sql = "INSERT INTO user_prefs VALUES (?,?,?)"
            c.execute(sql, (username, k, v))
            self.conn.commit()
        # print self.get_user_pref(username,k)

        c.close()

    def delete_user_pref(self, k):
        username = self.username
        print("delete_user_pref (%s,%s): " % (username,k))
        c = self.conn.cursor()
        sql = "DELETE FROM user_prefs WHERE username = ? AND key = ?"
        c.execute(sql, (username, k))
        self.conn.commit()
        return 

    def get_user_project_pref(self, username, project, k):
        # print "get_user_pref (%s,%s): " % (username,k)
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM user_project_prefs WHERE username = ? AND project = ? AND key = ?"
        c.execute(sql, (username, project, k))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
        return v

    def put_user_project_pref(self, username, project, k, v):
        # print "put_user_pref (%s,%s,%s): "% (username,k,v)
        if not username or not project or not k or not v:
            print("not storing nulls")
            return  # don't store null values
        c = self.conn.cursor()
        if self.get_user_project_pref(username, project, k):
            sql = "UPDATE user_project_prefs SET value = ? WHERE username = ? AND project = ? AND key = ?"
            c.execute(sql, (v, username, project, k))
        else:
            sql = "INSERT INTO user_project_prefs VALUES (?,?,?,?)"
            c.execute(sql, (username, project, k, v))
        self.conn.commit()
        c.close()

    def get_doc(self, uid):
        """Get a doc or None."""

        doc = None
        sql = "select uid,name,location,kind FROM document WHERE uid = ?"
        c = self.conn.cursor()
        c.execute(sql, (uid,))
        row = c.fetchone()
        if row:
            doc = Document(self, row[0], row[1], row[2], row[3])
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

    def search_names(self, name_frag, exact=False):
        """Get docs with LIKE unless matching exactly."""

        c = self.conn.cursor()

        if not exact:
            sql = "SELECT uid,name,location,kind FROM document WHERE name LIKE ?"
            c.execute(sql, ("%" + name_frag + "%",))
        else:
            sql = "SELECT uid,name,location,kind FROM document WHERE name = ?"
            c.execute(sql, (name_frag,))

        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self, row[0], row[1], row[2], row[3]))
        c.close()
        return docs

    def get_docs(self, tag_objects=[]):
        """Get all docs using the index.

        Does not get remote.

        tags is a list of tagid's. These must have been
        put together correctly before passing them here.

        """
        where_tags = ''
        if tag_objects:
            tags = ",".join(["'" + tag.tagid + "'" for tag in tag_objects])
            where_tags = " WHERE uid IN (SELECT uid FROM tagdoc WHERE tagid IN (%s))" % tags
        sql = "SELECT uid, name, location, kind FROM document "
        if where_tags:
            sql += where_tags
        c = self.conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self, row[0], row[1], row[2], row[3]))
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

        sql = "SELECT uid,name,location,kind FROM document WHERE uid = ?"
        c = self.conn.cursor()
        c.execute(sql, (uid,))
        row = c.fetchone()
        if not row:
            return None
        return Document(self, row[0], row[1], row[2], row[3])

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

    def create_document(self, name, location, kind, content=None, symlink_source_path=None):
        if not location:
            location = self.location
        uid = str(uuid.uuid1())
        path = os.path.join(self.get_storage_directory(), location, uid)
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
        # make this the current document
        self.put_user_pref('current_doc', uid)

        return self.get_doc(uid)

    def import_document(self, uid, name, location, kind, content):
        if not location:
            location = self.location
        path = os.path.join(self.get_storage_directory(), location, uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path, "doc." + kind.lower())
        self.touch(p)
        if os.path.exists(p):
            self.index_doc(uid, name, location, kind)
        doc = self.get_doc(uid)
        doc.put_content(content)
        return doc

