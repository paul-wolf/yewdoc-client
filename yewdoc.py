# -*- coding: utf-8 -*-
import os
import io
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
import webbrowser
import tempfile
import re
import string
import difflib
import re
import humanize as h
from jinja2 import Template


try:
    import pypandoc
except:
    print "pypandoc won't load. convert cmd will not work"

# suppress pesky warnings while testing locally
requests.packages.urllib3.disable_warnings()


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def is_binary_string():
    textchars = bytearray([7, 8, 9, 10, 12, 13, 27]) + bytearray(range(0x20, 0x100))
    return bool(bytes.translate(None, textchars))


def is_binary_file(fullpath):
    return is_binary_string(open(fullpath, 'rb').read(1024))


def slugify(value):
    """Stolen from Django: convert name.
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    #... re.sub('[-\s]+', '-', value)
    value = '-'.join(value.split()).lower()
    return value


def err():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=5, file=sys.stdout)


def is_uuid(uid):
    """Return non-None if uid is a uuid."""
    uuidregex = re.compile('[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}\Z', re.I)
    return uuidregex.match(uid)


def is_short_uuid(s):
    """Return non-None if uid is a uuid."""
    uuid_short_regex = re.compile('[0-9a-f]{8}\Z', re.I)
    return uuid_short_regex.match(s)


def get_short_uid(s):
    return s.split('-')[0]


def delete_directory(folder):
    """Delete directory p and all sub directories and files."""
    try:
        shutil.rmtree(folder)
    except Exception as e:
        print e


def get_sha_digest(s):
    """Generate digest for s.

    Trim final whitespace.
    Make sure it's utf-8.

    """
    s = s.rstrip()
    s = s.encode('utf-8')
    return hashlib.sha256(s).hexdigest()


def to_utc(dt):
    """Convert datetime object to utc."""
    local_tz = tzlocal.get_localzone().localize(dt)
    return local_tz.astimezone(pytz.utc)


def modification_date(path):
    """Get modification date of path as UTC time."""
    t = os.path.getmtime(path)
    return to_utc(datetime.datetime.fromtimestamp(t))


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
        self.path = os.path.join(store.get_storage_directory(), location, uid, "doc." + kind)
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
        return "%s.%s" % (self.get_basename(), self.kind)

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
        self.token = "Token %s" % self.store.get_user_pref('location.default.token')
        self.headers = {'Authorization': self.token, "Content-Type": "application/json"}
        self.url = self.store.get_user_pref('location.default.url')
        self.verify = False
        self.basic_auth_user = "yewser"
        self.basic_auth_pass = "yewleaf"
        self.basic_auth = False

        # if store thinks we are offline
        self.offline = store.offline

    def check_data(self):
        if not self.token or not self.url:
            raise RemoteException("""Token and url required to reach server. Check user prefs.
            Try: 'yd configure'""")

    def get_headers(self):
        """Get headers used for remote calls."""
        return self.headers

    def get(self, endpoint, data={}):
        """Perform get on remote with endpoint."""
        self.check_data()
        url = "%s/api/%s/" % (self.url, endpoint)
        return requests.get(url, headers=self.headers, params=data, verify=self.verify)

    def post(self, endpoint, data={}):
        """Perform post on remote."""
        url = "%s/api/%s/" % (self.url, endpoint)
        return requests.post(url, headers=self.headers, data=json.dumps(data), verify=self.verify)

    def unauthenticated_post(self, endpoint, data={}):
        url = "%s/%s/" % (self.url, endpoint)
        return requests.post(url, headers=self.headers, data=json.dumps(data), verify=self.verify)

    def delete(self, endpoint):
        """Perform delete on remote."""
        if self.offline:
            raise OfflineException()
        self.check_data()
        url = "%s/api/%s/" % (self.url, endpoint)
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

    def ping(self):
        """Call remote ping() method."""
        if self.offline:
            raise OfflineException()
        try:
            return self.get("ping")
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
        r = yew.remote.get("document")
        try:
            response = json.loads(r.content)
            # print r.content
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
        STATUS_NO_CONNECTION: "can't connect",
        STATUS_REMOTE_SAME: "documents are the same",
        STATUS_REMOTE_NEWER: "remote is newer",
        STATUS_REMOTE_OLDER: "remote is older",
        STATUS_DOES_NOT_EXIST: "remote does not exist",
        STATUS_REMOTE_DELETED: "remote was deleted",
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

    def push_doc(self, doc):
        """Serialize and send document.

        This will create the document on the server unless it exists.
        If it exists, it will be updated.

        """
        if self.offline:
            raise OfflineException()

        status = self.doc_status(doc.uid)

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
        return status

    def register(self, username, password, email, first_name, last_name):
        """Register a remote user.

        Raise exceptions if user exists or missing or invalid data.

        """
        if self.offline:
            raise OfflineException()
        data = {
            "username": username,
            "password": password,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }

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
        r = requests.post(url, data=json.dumps(tag_data), headers=self.headers, verify=self.verify)

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



    def pull_tags(self):
        """Pull tags from server.

        """
        if self.offline:
            raise OfflineException()
        
        url = "%s/api/tag_list/" % (self.url)
        r = requests.get(url, headers=self.headers, verify=self.verify)
        return r.content


class YewStore(object):
    """Our data store.

    Persistent user and project preferences.

    """

    yewdb_path = None
    conn = None

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

    def get_user_directory(self, username=None):
        """Get the directory for the current local user.

        Expand home and then find current yewdocs user.

        If username is not None, use that as user name.

        """
        home = expanduser("~")
        if not username:
            username = 'yewser'
        yew_dir = os.path.join(home, '.yew.d', username)
        if not os.path.exists(yew_dir):
            os.makedirs(yew_dir)
        return yew_dir

    def __init__(self):
        """Make sure storage is setup."""

        yew_dir = self.get_user_directory()
        self.yewdb_path = os.path.join(yew_dir, 'yew.db')
        self.conn = self.make_db(self.yewdb_path)
        # TODO: change this to be the same as get_user_directory()
        self.username = self.get_global('username', YewStore.DEFAULT_USERNAME)
        self.offline = self.get_global('offline', False)
        self.location = 'default'

    def get_storage_directory(self):
        """Return path for storage."""
        yew_dir = self.get_user_directory()
        return yew_dir

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
           folder_id,
           FOREIGN KEY(folderid) REFERENCES folder(folder_id)
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
        tags = []
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
        v = None
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
            print "not storing nulls"
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
        print "delete_user_pref (%s,%s): " % (username,k)
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
            print "not storing nulls"
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
            sql = "select uid,name,location,kind FROM document WHERE name LIKE ?"
            c.execute(sql, ("%" + name_frag + "%",))
        else:
            sql = "select uid,name,location,kind FROM document WHERE name = ?"
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
        doc = None
        sql = "select uid,name,location,kind FROM document "
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
        doc = None
        sql = "select uid,name,location,kind FROM document WHERE uid = ?"
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


class YewCLI(object):
    """Wraps two principle classes.

    We manage the store and remote objects.

    """

    def __init__(self):
        """Initialize."""

        self.store = YewStore()
        self.remote = Remote(self.store)


@click.group()
@click.option('--user', help="User name", required=False)
def cli(user):
    pass


@cli.command()
def status():
    """Print info about current setup."""
    click.echo("User     : %s" % yew.store.username)
    click.echo("Storage  : %s" % yew.store.get_storage_directory())
    click.echo("Offline  : %s" % yew.store.offline)


@cli.command()
@click.argument('name', required=False)
@click.option('--location', help="Location endpoint alias for document", required=False)
@click.option('--kind', '-k', default='md', help="Type of document, txt, md, rst, json, etc.", required=False)
def create(name, location, kind):
    """Create a new document."""
    if not name:
        docs = yew.store.search_names("%s")
        for index, doc in enumerate(docs):
            click.echo("%s [%s]" % (doc.name, doc.kind))

        sys.exit(0)

    # get the type of file
    kind_tmp = yew.store.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp

    if not location:
        location = 'default'

    doc = yew.store.create_document(name, location, kind)

    click.echo("created document: %s" % doc.uid)
    click.edit(require_save=True, filename=doc.path)
    yew.remote.push_doc(yew.store.get_doc(doc.uid))


def get_user_email():
    """Get user email from prefs or stdin."""
    self.url = self.store.get_user_pref('url')


@cli.command()
def make_db():
    self.make_db(yew.store.yewdb_path)


@cli.command()
@click.argument('tagname', required=False)
@click.argument('docname', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--create', '-c', is_flag=True, required=False)
@click.option('--untag', '-u', is_flag=True, required=False, help="Remove a tag association from document(s)")
def tag(tagname, docname, list_docs, create, untag):
    """Manage tags.

    Use this command to create tags, associate them with documents and
    remove tags.

    """

    tag = None
    if tagname:
        tagname = tagname.lower()
    if tagname and create:
        tag = yew.store.get_or_create_tag(tagname)
        click.echo("created: %s %s" % (tag.tagid, tag.name))
    elif create and not tagname:
        click.echo("tag name required")
    elif tagname and docname:
        if not tag:
            tags = yew.store.get_tags(tagname, exact=True)
        if len(tags) > 0:
            tag = tags[0]
        if not tag:
            click.echo("No tags found")
            sys.exit(0)
        docs = get_document_selection(docname, list_docs, multiple=True)
        if docs and isinstance(docs, list):
            for doc in docs:
                if untag:
                    yew.store.dissociate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s removed" % (tag.name, doc.name))
                else:
                    yew.store.associate_tag(doc.uid, tag.tagid)
                    click.echo("%s => %s" % (tag.name, doc.name))
        elif docs:
            doc = docs
            if untag:
                yew.store.dissociate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s removed" % (tag.name, doc.name))
            else:
                yew.store.associate_tag(doc.uid, tag.tagid)
                click.echo("%s => %s" % (tag.name, doc.name))
    else:
        # list tags
        tags = yew.store.get_tags(tagname)
        for tag in tags:
            click.echo(tag.name)


@cli.command()
@click.option('--tag', '-t', required=False, help="Set a tag as a filter.")
@click.option('--clear', '-c', is_flag=True, required=False, help="Clear the context.")
def context(tag, clear):
    """Set or unset a context.

    A context is essentially a filter. When a context, like a tag is
    set, operations that list documents will filter the
    documents. Like the `ls` command with a context of `-t foo` will
    only list documents tagged with `foo`.

    Use `--clear` to clear the context.

    Currently, only a single tag is allowed for context.

    """
    tags = None
    current_tag_context = yew.store.get_user_pref('tag_context')
    if tag:
        # lookup tag
        tags = yew.store.get_tags(tag, exact=True)
        if not tags:
            click.echo("Tag not found; must be exact match")
            sys.exit(1)
        elif len(tags) > 1:
            click.echo("More than one tag found. Only one tag allowed. Tags matching: %s" % ", ".join(tags))
            sys.exit(1)
        yew.store.put_user_pref('tag_context',tags[0].tagid)
        current_tag_context = yew.store.get_user_pref('tag_context')

    if clear:
        yew.store.delete_user_pref('tag_context')
        current_tag_context = yew.store.get_user_pref('tag_context')

    if current_tag_context:
        click.echo("current tag context: %s" % yew.store.get_tag(current_tag_context))

@cli.command()
@click.argument('name', required=False)
@click.argument('value', required=False)
def global_pref(name, value):
    """Show or set global preferences.

    No name for preference will show all preferences.
    Providing a value will set to that value.

    """
    if not name:
        prefs = yew.store.get_globals()
        for pref in prefs:
            click.echo("%s = %s" % (pref))
    elif value:
        # we are setting a value on the name
        yew.store.put_global(name, value)
    else:
        click.echo("%s = %s" % (name, yew.store.get_global(name)))


@cli.command()
@click.argument('name', required=False)
@click.argument('value', required=False)
def user_pref(name, value):
    """Show or set global preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    # get user first of all
    username = yew.store.get_global('username')
    if not name:
        for k in YewStore.user_preferences:
            v = yew.store.get_user_pref(k)
            click.echo("%s = %s" % (k, v))
    elif value:
        # set the user preference
        yew.store.put_user_pref(name, value)
    else:
        click.echo("%s = %s" % (name, yew.store.get_user_pref(name)))


def parse_ranges(s):
    """Parse s as a list of range specs."""
    l = []  # return value is a list of doc indexes
    ranges = s.split(',')
    # list of ranges
    for r in ranges:
        try:
            i = int(r)
            l.append(i)
        except ValueError:
            # check if range
            if '-' in r:
                start, end = r.split('-')
                start = int(start)
                end = int(end)
                l.extend([x for x in range(start, end + 1)])
    return l


def document_menu(docs, multiple=False):
    """Show list of docs. Return selection."""
    if not len(docs):
        return None
    for index, doc in enumerate(docs):
        click.echo("%s) %s" % (index, doc.name))
    if multiple:
        v = click.prompt('Select document')
        index_list = parse_ranges(v)
        l = []
        for i in index_list:
            if i in range(len(docs)):
                l.append(docs[i])
        return l  # returning a list of docs!!
    else:
        v = click.prompt('Select document', type=int)
        if not v in range(len(docs)):
            print "Choice not in range"
            sys.exit(1)
    return docs[v]


def get_document_selection(name, list_docs, multiple=False):
    """Present lists or whatever to get doc choice.

    name (str): a title or partial title to use as search
    list_docs (bool): a flag to list documents are not.
    ranges (bool): allow range of integers for a list selection?

    If there is no name, show recent list.
    otherwise, show all docs

    We let user specify if a list of docs should be returned.
    In that case, the return value's type is a list.

    """

    if name and is_uuid(name):
        return yew.store.get(name)

    if name and is_short_uuid(name):
        return yew.store.get_short(name)

    if not name and not list_docs:
        docs = yew.store.get_recent('yewser')
        return document_menu(docs, multiple)
    elif list_docs:
        docs = yew.store.get_docs()
        if len(docs) == 1:
            return docs[0]
        return document_menu(docs, multiple)
    elif name:
        docs = yew.store.search_names(name)
        if len(docs) == 1:
            return docs[0]
        return document_menu(docs, multiple)
    return doc


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--open-file', '-o', is_flag=True, required=False, help="Open the file in your host operating system.")
def edit(name, list_docs, open_file):
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

    doc = get_document_selection(name, list_docs)

    # if doc is null, we didn't find one, ask if we should create:
    if not doc:
        if click.confirm("Couldn't find that document, shall we create it?"):
            doc = yew.store.create_document(name, location='default', kind='md')
        else:
            sys.exit(0)

    if open_file:
        # send to host os to ask it how to open file
        click.launch(doc.get_path())
    else:
        click.edit(editor='emacs', require_save=True, filename=doc.path)

    yew.remote.push_doc(yew.store.get_doc(doc.uid))
    yew.store.put_user_pref('current_doc', doc.uid)
    yew.store.update_recent('yewser', doc)


@cli.command()
@click.argument('spec', required=True)
@click.option('--string-only', '-s', is_flag=True, required=False)
@click.option('--insensitive', '-i', is_flag=True, required=False)
#@click.option('--remote','-r',is_flag=True, required=False)
def find(spec, string_only, insensitive):
    """Search for spec in contents of docs.

    spec is a regular expression unless string-only is selected
    in which case a simple string match is used.

    """

    docs = yew.store.get_docs()

    for doc in docs:
        found = False
        if string_only:
            if not insensitive:
                if spec in doc.get_content():
                    found = True
            else:
                if spec.lower() in doc.get_content().lower():
                    found = True
        elif re.search(spec, doc.get_content()):
            found = True

        if found:
            click.echo(doc.name)


@cli.command()
@click.argument('name', required=False)
@click.option('--info', '-l', is_flag=True, required=False)
@click.option('--remote', '-r', is_flag=True, required=False)
@click.option('--humanize', '-h', is_flag=True, required=False)
@click.option('--tags', '-t', required=False)
def ls(name, info, remote, humanize, tags):
    """List documents."""

    if remote:
        response = yew.remote.get_docs()
        for doc in response:
            click.echo("%s %s" % (get_short_uid(doc['uid']), doc['title']))

        sys.exit(0)
    tag_objects = []
    if tags:
        tag_objects = yew.store.parse_tags(tags)
    else:
        # check for context
        current_tag_context = yew.store.get_user_pref('tag_context')
        if current_tag_context:
            tag_objects = [yew.store.get_tag(current_tag_context)]
            click.echo("Current tag context: %s" % str(tag_objects[0]))
    if name:
        docs = yew.store.search_names(name)
    else:
        docs = yew.store.get_docs(tag_objects=tag_objects)
    for doc in docs:
        if info:
            if doc.is_link():
                click.echo("ln ", nl=False)
            else: 
                click.echo("   ", nl=False)
            click.echo(doc.short_uid(), nl=False)
            click.echo("   ", nl=False)
            click.echo(doc.kind.rjust(5), nl=False)
            click.echo("   ", nl=False)
            if humanize:
                click.echo(h.naturalsize(doc.get_size()).rjust(10), nl=False)
            else:
                click.echo(str(doc.get_size()).rjust(10), nl=False)
            click.echo("   ", nl=False)
            if humanize:
                click.echo(h.naturaltime(doc.get_last_updated_utc().replace(tzinfo=None)).rjust(15), nl=False)
            else:
                click.echo(doc.get_last_updated_utc().replace(tzinfo=None), nl=False)
            click.echo("   ", nl=False)
        click.echo(doc.name, nl=False)
        if info:
            click.echo("   ", nl=False)
            #click.echo(slugify(doc.name), nl=False)
        click.echo('')


@cli.command()
@click.argument('name', required=False)
@click.option('--force', '-f', is_flag=True, required=False, 
              help="Don't confirm deletes")
@click.option('--prune', '-p', is_flag=True, required=False, 
              help="Delete local docs marked as deleted on server")
def sync(name, force, prune):
    """Pushes local docs and pulls docs from remote.

    We don't overwrite newer docs.
    Does nothing if docs are the same.

    """
    # make sure we are online
    try:
        r = yew.remote.ping()
    except OfflineException:
        click.echo("can't sync in offline mode")

    # get local docs
    docs_local = yew.store.get_docs()
    docs_remote = yew.remote.get_docs()
    remote_done = []

    for doc in docs_local:
        print doc.name.ljust(50), '\r',
        c = yew.remote.doc_status(doc.uid)
        if c == Remote.STATUS_REMOTE_SAME:
            remote_done.append(doc.uid)
        elif c == Remote.STATUS_REMOTE_NEWER:
            click.echo("get newer content from remote: %s %s" % (doc.short_uid(), doc.name))
            remote_doc = yew.remote.fetch(doc.uid)
            # a dict
            doc.put_content(remote_doc['content'])
            if not remote_doc['title'] == doc.name:
                yew.store.rename_doc(doc, remote_doc['title'])
            remote_done.append(doc.uid)
        elif c == Remote.STATUS_REMOTE_OLDER:
            click.echo("push newer content to remote : %s %s" % (doc.short_uid(), doc.name))
            yew.remote.push_doc(doc)
            remote_done.append(doc.uid)
        elif c == Remote.STATUS_DOES_NOT_EXIST:
            click.echo("push new doc to remote       : %s %s" % (doc.short_uid(), doc.name))
            yew.remote.push_doc(doc)
            remote_done.append(doc.uid)
        elif c == Remote.STATUS_REMOTE_DELETED:
            click.echo("remote was deleted           : %s %s" % (doc.short_uid(), doc.name))
            if prune:
                yew.store.delete_document(doc)
                click.echo("pruned local")
        else:
            raise Exception("Invalid remote status   : %s for %s" % (c, str(doc)))

    print ''.ljust(50), '\r'

    remote_docs = yew.remote.get_docs()
    for rdoc in remote_docs:
        if rdoc['uid'] in remote_done:
            continue
        remote_doc = yew.remote.fetch(rdoc['uid'])
        click.echo("importing doc: %s %s" % (remote_doc['uid'].split('-')[0], remote_doc['title']))
        yew.store.import_document(remote_doc['uid'],
                                  remote_doc['title'],
                                  'default',
                                  remote_doc['kind'],
                                  remote_doc['content'])

    
    yew.remote.push_tag_associations()
            
    tags = yew.store.get_tags('')
    if len(tags) > 0:
        click.echo("syncing tags")
        tag_data = {}
        for tag in tags:
            tag_data[tag.tagid] = tag.name
        #print yew.remote.pull_tags()
        yew.remote.push_tags(tag_data)

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--force', '-f', is_flag=True, required=False)
@click.option('--remote', '-r', is_flag=True, required=False)
def delete(name, list_docs, force, remote):
    """Delete a document.

    To delete a remote document, it needs to be local. So,
    you may need to sync it from remote before deleting it.

    """

    docs = get_document_selection(name, list_docs, multiple=True)
    if not docs:
        click.echo("no matching documents")
        return
    if not isinstance(docs, list):
        docs = [docs]
    for doc in docs:
        click.echo("Document: %s  %s" % (doc.uid, doc.name))
    d = True
    if not force:
        d = click.confirm('Do you want to continue to delete the document(s)?')
    if d:
        for doc in docs:
            yew.store.delete_document(doc)
            if remote:
                yew.remote.delete("document/%s" % doc.uid)
                click.echo("removed %s" % doc.name)


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--remote', '-r', is_flag=True, required=False)
def show(name, list_docs, remote):
    """Send contents of document to stdout."""

    doc = get_document_selection(name, list_docs)
    if remote:
        remote_doc = yew.remote.fetch(doc.uid)
        if remote_doc:
            click.echo(remote_doc['content'])
    else:
        if doc:
            click.echo(doc.get_content())
        else:
            click.echo("no matching documents")
    sys.stdout.flush()


def diff_content(doc1, doc2):
    #d = difflib.Differ()
    #diff = d.compare(doc1,doc2)
    diff = difflib.ndiff(doc1, doc2)
    click.echo('\n'.join(list(diff)))


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--remote', '-r', is_flag=True, required=False)
@click.option('--diff', '-d', is_flag=True, required=False)
def describe(name, list_docs, remote, diff):
    """Show document details."""

    doc = get_document_selection(name, list_docs)
    if doc:
        doc.dump()
    status = None
    if remote:
        r_info = yew.remote.doc_exists(doc.uid)
        click.echo("Remote: ")
        for k, v in r_info.items():
            click.echo("%s: %s" % (k, v))
        status = yew.remote.doc_status(doc.uid)
        click.echo(Remote.STATUS_MSG[status])
    if doc and diff and not status == Remote.STATUS_REMOTE_SAME \
       and not Remote.STATUS_NO_CONNECTION:
        remote_doc = yew.remote.fetch(doc.uid)
        s = diff_content(
            remote_doc['content'].rstrip().splitlines(),
            doc.get_content().rstrip().splitlines()
        )
        click.echo(s)


@cli.command()
@click.argument('name1', required=True)
@click.argument('name2', required=True)
def diff(name1, name2):
    doc1 = get_document_selection(name1, list_docs=False)
    doc2 = get_document_selection(name2, list_docs=False)
    """Compare two documents."""

    s = diff_content(
        doc1.get_content().rstrip().splitlines(),
        doc2.get_content().rstrip().splitlines()
    )
    click.echo(s)


@cli.command()
def push():
    """Push all documents to the server."""
    if yew.remote.offline:
        pass
    docs = yew.store.get_docs()
    result = ""
    for doc in docs:
        click.echo("pushing: %s:" % doc.name, nl=False)
        status = yew.remote.push_doc(doc)
        if status == Remote.STATUS_REMOTE_SAME:
            result = " No difference"
        elif status == Remote.STATUS_REMOTE_NEWER:
            result = " can't push because remote newer"
        elif status == Remote.STATUS_REMOTE_OLDER:
            result = " local newer, pushed"
        elif status == Remote.STATUS_DOES_NOT_EXIST:
            result = " no remote version, creating"
        click.echo(result)
    click.echo("Done!")


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def head(name, list_docs):
    """Send start of document to stdout."""

    doc = get_document_selection(name, list_docs)
    click.echo(doc.get_content()[:250])


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def tail(name, list_docs):
    """Send end of document to stdout."""

    doc = get_document_selection(name, list_docs)
    click.echo(doc.get_content()[-250:])


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def rename(name, list_docs):
    """Send contents of document to stdout."""

    doc = get_document_selection(name, list_docs)
    click.echo("Rename: '%s'" % doc.name)
    v = click.prompt('Enter the new document title ', type=unicode)
    if v:
        doc = yew.store.rename_doc(doc, v)
    yew.remote.push_doc(doc)


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def kind(name, list_docs):
    """Change kind of document."""

    doc = get_document_selection(name, list_docs)
    click.echo(doc)
    click.echo("Current document kind: '%s'" % doc.kind)
    for i, d in enumerate(yew.store.doc_kinds):
        click.echo("%s" % (d))
    kind = click.prompt('Select the new document kind ', type=str)
    #kind = yew.store.doc_kinds[v]
    click.echo("Changing document kind to: %s" % kind)
    doc = yew.store.change_doc_kind(doc, kind)
    yew.remote.push_doc(doc)


@cli.command()
def ping():
    """Ping server."""
    r = yew.remote.ping()
    if not r:
        sys.exit(1)
    if r.status_code == 200:
        sdt = dateutil.parser.parse(json.loads(r.content))
        click.echo("Server time  : %s" % sdt)
        click.echo("Skew         : %s" % str(datetime.datetime.now() - sdt))
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)


@cli.command()
def api():
    """Get API of the server."""
    r = yew.remote.api()
    if not r:
        sys.exit(1)
    if r.status_code == 200:
        # content should be server time
        click.echo(r.content)
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def browse(name, list_docs):
    """Convert to html and attempt to load in web browser."""

    input_formats = ['md', 'rst']
    #doc = get_document_selection(name,list_docs)
    docs = yew.store.get_docs()
    nav = ''
    for doc in docs:
        tmp_dir = yew.store.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        a = '<a href="file://%s">%s</a><br/>\n' % (tmp_file, doc.name)
        nav += a
    for doc in docs:
        if doc.kind == 'md':
            html = markdown.markdown(doc.get_content())
        else:
            if not doc.kind in input_formats:
                kind = 'md'
            else:
                kind = doc.kind
            html = pypandoc.convert(
                doc.get_path(),
                format=kind,
                to='html'

            )
        tmp_dir = yew.store.get_tmp_directory()
        tmp_file = os.path.join(tmp_dir, doc.get_safe_name() + ".html")
        with click.open_file('template_0.html', 'r') as f:
            t = f.read()

        template = Template(t)
        data = {
            "title": doc.name,
            "content": html,
            "nav": nav
        }
        dest = template.render(data)

        # template = string.Template(t)
        # dest = template.substitute(
        #     title=doc.name,
        #     content=html,
        #     nav=nav
        # )
        f = codecs.open(tmp_file, 'w', 'utf-8').write(dest)
    click.launch(tmp_file)


@cli.command()
@click.argument('name', required=False)
@click.argument('destination_format', required=True)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--formats', '-f', is_flag=True, required=False)
def convert(name, destination_format, list_docs, formats):
    """Convert to destination_format and print to stdout."""

    if formats:
        formats = pypandoc.get_pandoc_formats()
        click.echo("Input formats:")
        for f in formats[0]:
            click.echo("\t" + f)
        click.echo("Output formats:")
        for f in formats[1]:
            click.echo("\t" + f)
        sys.exit(0)

    doc = get_document_selection(name, list_docs)
    # click.echo(doc.name)
    # click.echo(doc.kind)
    # click.echo(destination_format)

    dest = pypandoc.convert(doc.get_content(),
                            format=doc.kind,
                            to=destination_format)
    click.echo(dest)
    sys.stdout.flush()


@cli.command()
@click.argument('path', required=True)
@click.option('--kind', '-k', required=False)
@click.option('--force', '-f', is_flag=True, required=False)
@click.option('--symlink', '-s', is_flag=True, required=False)
def take(path, kind, force, symlink):
    """Import a file as a document.

    The base filename becomes the document title.

    Should be a text type, but we leave that to user.

    --force will cause a similarly titled document to be overwritten
    in the case of a name conflict.

    """
    if not os.path.exists(path) or not os.path.isfile(path):
        click.echo("path does not exist: %s" % path)
        sys.exit(1)

    content = None

    # slurp file
    if not symlink:
        with click.open_file(path, 'r', 'utf-8') as f:
            content = f.read()

    filename, file_extension = os.path.splitext(path)

    # try to figure out what kind of file it is
    # don't get confused by files starting with dot
    if not kind and not filename.startswith('.'):
        # get the extension of the file without dot
        if '.' in path:
            kind = path.split('.')[-1]
    if not kind:
        kind = yew.store.get_user_pref('default_doc_type')
    if not kind:
        # because the user pref might be null
        kind = "md"

    title = os.path.splitext(path)[0]
    # check if we have one with this title
    # the behaviour we want is for the user to continuously
    # ingest the same file that might be updated out-of-band
    # TODO: handle multiple titles of same name
    docs = yew.store.search_names(title, exact=True)
    if docs and not symlink:
        if len(docs) == 1:
            if not force:
                click.echo("A document with this title exists already")
            if force or click.confirm("Overwrite existing document: %s ?" % docs[0].name):
                docs[0].put_content(unicode(content))
                yew.remote.push_doc(docs[0])
                sys.exit(0)

    if symlink:
        doc = yew.store.create_document(title, 
                                        'default', 
                                        kind,
                                        symlink_source_path=path)
        click.echo("Symlinked: %s" % doc.uid)
    else:
        doc = yew.store.create_document(title, 'default', kind)
        doc.put_content(unicode(content))
    yew.remote.push_doc(doc)


@cli.command()
@click.argument('name', required=False)
@click.argument('path', required=True)
@click.option('--list_docs', '-l', is_flag=True, required=False)
def attach(name, path, list_docs):
    """Take a file and put into media folder.

    The filename will be stripped of spaces.

    """

    if not os.path.exists(path) or not os.path.isfile(path):
        click.echo("file does not exist: %s" % path)
        sys.exit(1)

    doc = get_document_selection(name, list_docs)

    _, filename = os.path.split(path)
    dest_path = os.path.join(doc.get_media_path(), filename)

    # copy file
    with click.open_file(path, 'r') as f_in:
        with click.open_file(dest_path, 'w') as f_out:
            f_out.write(f_in.read())


def _configure():
    """Prompt user for settings necessary for remote operations.

    Store in user prefs.
    Skip secret things like tokens and passwords.

    """
    # the preferences need to be in the form:
    # location.default.username
    for pref in yew.store.user_preferences:
        if 'token' in pref or 'password' in pref:
            continue
        d = yew.store.get_user_pref(pref)
        p = pref.split('.')
        i = p[2]
        value = click.prompt("Enter %s" % i, default=d, type=str)
        click.echo(pref + "==" + value)
        yew.store.put_user_pref(pref, value)


@cli.command()
def configure():
    """Get configuration information from user."""
    _configure()


@cli.command()
def register():
    """Try to get a user account on remote."""

    # first make sure we are configured
    #_configure()

    # next make sure we have a connection to the server
    if not yew.remote.unauthenticated_ping():
        click.echo("Could not connect")
        sys.exit(1)

    username = yew.store.get_user_pref("location.default.username")
    email = yew.store.get_user_pref("location.default.email")
    first_name = yew.store.get_user_pref("location.default.first_name")
    last_name = yew.store.get_user_pref("location.default.last_name")
    p = SG("[\w\d]{12}").render()
    password = click.prompt("Enter a new password or accept the default ", default=p, type=str)
    r = yew.remote.register_user(data={
        "username": username,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
    })
    if r.status_code == 200:
        data = json.loads(r.content)
        yew.store.put_user_pref("location.default.token", data['token'])
    else:
        click.echo("Something went wrong")
        click.echo("status code: %s" % r.status_code)
        click.echo("response: %s" % r.content)


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs', '-l', is_flag=True, required=False)
@click.option('--location', required=False)
@click.option('--kind', '-k', required=False)
@click.option('--create', '-c', is_flag=True, required=False, help="Create a new document")
@click.option('--append', '-a', is_flag=True, required=False, help="Append to an existing document")
def read(name, list_docs, location, kind, create, append):
    """Get input from stdin and either create a new document or append to and existing.

    --create and --append are mutually exclusive.
    --create requires a name.
    """

    if create and append:
        click.echo("create and append are mutually exclusive")
        sys.exit(1)

    if create and not name:
        click.echo("a name must be provided when creating")
        sys.exit(1)

    #f = click.open_file('-','r')
    #f = sys.stdin

    content = ''

    # if sys.stdin.isatty() or True:
    #     content = sys.stdin.read()
    with click.open_file('-', 'r', 'utf-8') as f:
        content = f.read()

    if not (name or create or append):
        # we'll assume create
        # let's ask for a name
        name = click.prompt("Provide a title for the new document", type=str)
        create = True
        append = False

    # if name, we want to either 1) create new file with that name
    # or 2) we want to append or replace an existing one
    if append:
        doc = get_document_selection(name, list_docs)

    # get the type of file
    # we'll ignore this if appending
    kind_tmp = yew.store.get_user_pref("default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp
    else:
        kind = 'md'

    if not location:
        location = 'default'

    if create or not append:
        doc = yew.store.create_document(name, location, kind, content=content)
    else:
        s = doc.get_content() + content
        doc.put_content(s)

##### our one global ####
yew = YewCLI()

if __name__ == '__main__':
    cli()
