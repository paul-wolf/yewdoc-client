# -*- coding: utf-8 -*-
import os
import sys
import uuid
import traceback
from os.path import expanduser
import click
import sqlite3
import requests
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


requests.packages.urllib3.disable_warnings()

yew = None


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def err():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=5, file=sys.stdout)

def is_uuid(uid):
    """Return non-None if uid is a uuid."""
    uuidregex = re.compile('[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}\Z', re.I)
    return uuidregex.match(uid)

def delete_directory(folder):
    """Delete directory p and all sub directories and files."""
    try:
        shutil.rmtree(folder)    
    except Exception, e:
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

class Document(object):
    """Describes a document."""
    def __init__(self,store,uid,name,location,kind):
        self.uid = uid
        self.name = name
        self.location = location
        self.kind = kind
        self.path = os.path.join(store.get_storage_directory(),location,uid,"doc."+kind)
        self.digest = self.get_digest()
        self.directory_path = os.path.join(store.get_storage_directory(),location,uid)
        self.store = store

    def get_digest(self):
        return get_sha_digest(self.get_content())

    def get_path(self):
        return os.path.join(self.store.get_storage_directory(),self.location,self.uid,"doc."+self.kind)

    def validate(self):
        if not os.path.exists(self.get_path()):
            raise Exception("Non-existant document: %s" % self.path)
        # should also check that we are in sync with index
        return True

    def dump(self):
        click.echo("uid      : %s" % self.uid)
        click.echo("title    : %s" % self.name)
        click.echo("location : %s" % self.location)
        click.echo("kind     : %s" % self.kind)
        click.echo("digest   : %s" % self.digest)
        click.echo("path     : %s" % self.path)
        click.echo("Last modified: %s" % modification_date(self.get_path()))

    def get_last_updated_utc(self):
        return modification_date(self.get_path())

    def serialize(self, no_uid=False):
        """Serialize as json to send to server."""
        data = {}
        data['uid'] = self.uid
        data['parent'] = None
        data['title'] = self.name
        data['kind'] = self.kind
        data['content'] = self.get_content() # open(self.get_path()).read()
        data['digest'] = self.digest
        return json.dumps(data)

    def get_content(self):
        """Get the content."""
        f = codecs.open(self.path, "r", "utf-8")
        return f.read()

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

    global_preferences = [
        "username",
    ]

    user_preferences = [
        "yewdoc_email",
        "yewdoc_token",
        "yewdoc_url",
        "yewdoc_url.default",
        "default_doc_type",
        "current_doc",
    ]

    doc_kinds = [
        "md",
        "txt",
        "rst",
        "json",
    ]

    def __init__(self):
        home = expanduser("~")
        yew_dir = os.path.join(home,'.yew.d')
        if not os.path.exists(yew_dir):
            os.makedirs(yew_dir)
        self.yewdb_path = os.path.join(yew_dir,'yew.db')
        self.conn = self.make_db(self.yewdb_path)

    def get_storage_directory(self):
        """Return path for storage."""

        home = expanduser("~")
        yew_dir = os.path.join(home,'.yew.d')
        return yew_dir

    def make_db(self,path):
        """Create the tables if it does not exist and get or create tables."""
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS global_prefs (key, value)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_prefs (username, key, value)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_project_prefs (username, project, key, value)''')
        c.execute('''CREATE TABLE IF NOT EXISTS document (uid,name,location,kind,digest)''')
        conn.commit()
        return conn

    def delete_document(self,doc,local_only=True):
        """Delete a document and it's associated entities."""

        home = expanduser("~")
        yew_dir = os.path.join(home,'.yew.d')
        # remove record
        c = self.conn.cursor()
        sql = "DELETE FROM document WHERE uid = ?"
        c.execute(sql,(doc.uid,))

        # remove files
        path = doc.directory_path
        # sanity check
        if not path.startswith(yew_dir): 
            raise Exception("Path for deletion is wrong: %s" % path)
        shutil.rmtree(path)

        # tell server if removing remote
        if not local_only:
            # delete on server
            pass

        self.conn.commit()
        self.conn.close()

    def update_recent(self,username,doc):
        """Update most recent list.
        Return list of uids.
        """
        list_unparsed = self.get_user_pref(username,"recent_list")
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
        else:
            list_parsed = []
        if doc.uid in list_parsed:
            list_parsed.remove(doc.uid)  # take it out
        list_parsed.insert(0,doc.uid) # make it the first one
        # now save the new list
        self.put_user_pref(username,'recent_list',json.dumps(list_parsed))

    def get_recent(self,username):
        """Get most recent documents."""
        list_unparsed = self.get_user_pref(username,"recent_list")
        docs = []
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
            for uid in list_parsed:
                d = self.get_doc(uid)
                if d:
                    docs.append(d)
            return docs
        return []
        

    def get_global(self,k):
        #print "get_global (key): ", k
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM global_prefs WHERE key = ?"
        c.execute(sql,(k,))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
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

    def put_global(self,k,v):
        """Set a global preference. Must be in class var global_preferences."""
        if not k in YewStore.global_preferences:
            raise ValueError("Unknown global preference: %s. Choices are: %s" % (k,", ".join(YewStore.global_preferences)))
        print "put_global (%s,%s)" % (k,v)
        if not k or not v:
            print "not storing nulls"
            return # don't store null values
        c = self.conn.cursor()
        if self.get_global(k):
            sql = "UPDATE global_prefs SET value = ? WHERE key = ?"
            print "UPDATE global_prefs SET value = '%s' WHERE key = '%s'" % (v,k)
            c.execute(sql,(v,k,))
            click.echo("updated global: %s = %s" % (k, self.get_global(k)))
        else:
            sql = "INSERT INTO global_prefs VALUES (?,?)"
            c.execute(sql,(k,v,))
            click.echo("created global: %s = %s" % (k, self.get_global(k)))

        self.conn.commit()
        c.close()

    def get_user_pref(self,username,k):
        #print "get_user_pref (%s,%s): " % (username,k)
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM user_prefs WHERE username = ? AND key = ?"
        c.execute(sql,(username,k))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
        return v

    def put_user_pref(self,username,k,v):
        #print "put_user_pref (%s,%s,%s): "% (username,k,v)
        if not username or not k or not v:
            print "not storing nulls"
            return # don't store null values
        c = self.conn.cursor()
        if self.get_user_pref(username,k):
            sql = "UPDATE user_prefs SET value = ? WHERE username = ? AND key = ?"
            #print "UPDATE user_prefs SET value = %s WHERE username = %s AND key = %s" % (v,username,k)
            c.execute(sql,(v,username,k))
            self.conn.commit()
        else:
            sql = "INSERT INTO user_prefs VALUES (?,?,?)"
            c.execute(sql,(username,k,v))
            self.conn.commit()
        #print self.get_user_pref(username,k)

        c.close()

    def get_user_project_pref(self,username,project,k):
        #print "get_user_pref (%s,%s): " % (username,k)
        v = None
        c = self.conn.cursor()
        sql = "SELECT value FROM user_project_prefs WHERE username = ? AND project = ? AND key = ?"
        c.execute(sql,(username,project,k))
        row = c.fetchone()
        if row:
            v = row[0]
        c.close()
        return v

    def put_user_project_pref(self,username,project,k,v):
        #print "put_user_pref (%s,%s,%s): "% (username,k,v)
        if not username or not project or not k or not v:
            print "not storing nulls"
            return # don't store null values
        c = self.conn.cursor()
        if self.get_user_project_pref(username,project,k):
            sql = "UPDATE user_project_prefs SET value = ? WHERE username = ? AND project = ? AND key = ?"
            c.execute(sql,(v,username,project,k))
        else:
            sql = "INSERT INTO user_project_prefs VALUES (?,?,?,?)"
            c.execute(sql,(username,project,k,v))
        self.conn.commit()
        c.close()

    def get_doc(self,uid):
        """Get a doc or None."""
        doc = None
        sql = "select uid,name,location,kind FROM document WHERE uid = ?"
        c = self.conn.cursor()
        c.execute(sql,(uid,))
        row = c.fetchone()
        if row:
            doc = Document(self,row[0],row[1],row[2],row[3])
        c.close()
        return doc

    def change_doc_kind(self,doc,new_kind):
        """Change type of document."""
        path_src = doc.path
        doc.kind = new_kind
        path_dest = doc.get_path()
        os.rename(path_src,path_dest)
        self.reindex_doc(doc)
        return doc

        
    def rename_doc(self,doc,new_name):
        """Rename document with name."""

        doc.name = new_name
        self.reindex_doc(doc)

        # c = self.conn.cursor()
        # sql = "UPDATE document SET name = ? WHERE uid = ?"
        # c.execute(sql,(new_name,doc.uid))
        # self.conn.commit()
        # c.close()

        return doc


    def search_names(self,name_frag):
        """Get a doc via reged on name."""

        username = self.get_global('username')
        location_url = self.get_user_pref(username,'yewdoc_url.default')
        doc = None
        sql = "select uid,name,location,kind FROM document WHERE name LIKE ?"
        c = self.conn.cursor()
        c.execute(sql,("%"+name_frag+"%",))
        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self,row[0],row[1],row[2],row[3]))
        c.close()
        return docs

    def get_docs(self):
        """Get all docs."""

        username = self.get_global('username')
        location_url = self.get_user_pref(username,'yewdoc_url.default')
        doc = None
        sql = "select uid,name,location,kind FROM document"
        c = self.conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        docs = []
        for row in rows:
            docs.append(Document(self,row[0],row[1],row[2],row[3]))
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
            c.execute(sql,(uid,name,location,kind))
            self.conn.commit()
            c.close()

    def reindex_doc(self, doc):
        """Refresh index information."""
        # check if present
        #if not self.get_doc(doc.uid):
        #    raise Exception("Can't reindex non-existant document.")
        c = self.conn.cursor()
        sql = "UPDATE document SET name=?, location=?, kind=?, digest=? WHERE uid = ?"
        c.execute(sql,(doc.name, doc.location, doc.kind, doc.digest, doc.uid))
        self.conn.commit()
        c.close()
        return doc

    def get_headers(self):
        """Get headers."""
        username = self.get_global('username')
        yewdoc_token = "Token %s" % self.get_user_pref(username,'yewdoc_token')
        return {'Authorization': yewdoc_token, "Content-Type":"application/json"}


    def post_doc(self,doc):
        """Serialize and send document.
        
        This will create the document on the server unless it exists.
        If it exists, it will be updated. 

        """

        # check if it exists on the remote server
        rexists = yew.remote_exists(doc.uid)
        if rexists and rexists['digest'] == doc.get_digest():
            click.echo("Nothing to update")
            return 

        # check if remote is newer
        if rexists:
            remote_dt = dateutil.parser.parse(rexists['date_updated'])
            remote_newer = remote_dt > doc.get_last_updated_utc()
            if remote_newer:
                click.echo("Can't push to server because remote is newer.")
                return 

        username = self.get_global('username')
        location_url = self.get_user_pref(username,'yewdoc_url.default')
        data = doc.serialize()
        headers = self.get_headers()

        if rexists:
            # it exists, so let's put together the  update url and PUT it
            url = "%s/api/document/%s/" % (location_url,doc.uid)
            data = doc.serialize(no_uid=True)
            r = requests.put(url, data=data, headers=headers, verify=False)
        else:
            # create a new one
            url = "%s/api/document/" % location_url
            r = requests.post(url, data=data, headers=headers, verify=False)


class YewCLI(object):
    url = "https://yew.io/yewdoc"
    basic_auth_user = "yewser"
    basic_auth_pass = "yewleaf"
    basic_auth = False
    config_files = ('~/.yew')
    username = "yewser"
    password = "yewleaf"
    session_key = None
    api_name = "webapi"
    config = None
    verbose = False
    store = None
    location = 'default'
    current_uid = None

    def __init__(self):
        """Initialize."""
        self.store = YewStore()
        self.read_config()

    def read_config(self):
        try:
            # if not self.username:
            #     self.username = self.store.get_global('username')
            # if not self.username:
            #     raise Exception("No username provided.")
            # else:
            #     self.store.put_global('username',self.username)
            # self.password = self.store.get_user_pref(self.username,'password')
            # self.session_key = self.store.get_user_pref(self.username,'session_key')
            # self.url = self.store.get_user_pref(self.username,'url')
            # self.project = self.store.get_user_pref(self.username,'project')
            pass
        except Exception as e:
            raise e

    def save_config(self):
        """Save total configuration."""
        # self.store.put_global('username',self.username)
        # self.store.put_user_pref(self.username,'password',self.password)
        # self.store.put_user_pref(self.username,'session_key',self.session_key)
        # self.store.put_user_pref(self.username,'url',self.url)
        # self.store.put_user_pref(self.username,'project',self.project)
        pass

    def ping(self):
        username = yew.store.get_global('username')
        location_url = yew.store.get_user_pref(username,'yewdoc_url.default')
        yewdoc_token = "Token %s" % yew.store.get_user_pref(username,'yewdoc_token')
        headers = {'Authorization': yewdoc_token, "Content-Type":"application/json"}
        url = "%s/api/ping/" % location_url
        #click.echo(url)
        return requests.get(url, headers=headers, verify=False)

    def api(self):
        username = yew.store.get_global('username')
        location_url = yew.store.get_user_pref(username,'yewdoc_url.default')
        yewdoc_token = "Token %s" % yew.store.get_user_pref(username,'yewdoc_token')
        headers = {'Authorization': yewdoc_token, "Content-Type":"application/json"}
        url = "%s/api/" % location_url
        #click.echo(url)
        return requests.get(url, headers=headers, verify=False)

    def status(self):
        """Print status."""
        print "url: ", self.url
        print "username: ", self.username
        print "project: ", self.project
        print "card: ", self.card

    def get(self,endpoint,data={}):
        username = yew.store.get_global('username')
        location_url = yew.store.get_user_pref(username,'yewdoc_url.default')
        yewdoc_token = "Token %s" % yew.store.get_user_pref(username,'yewdoc_token')
        headers = {'Authorization': yewdoc_token, "Content-Type":"application/json"}
        url = "%s/api/%s/" % (location_url,endpoint)
        return requests.get(url, headers=headers, params=data, verify=False)

    def remote_exists(self,uid):
        """Check if a remote doc with uid exists. Return remote digest or None."""
        r = yew.get("exists",{"uid":uid})
        if r.status_code == 200:
            data = json.loads(r.content)
            if 'digest' in data:
                return data
        return None

    def touch(self,path):
        with codecs.open(path, "a", "utf-8"):
            os.utime(path, None)
    
    def create_document(self, name, location, kind):
        if not location:
            location = self.location
        uid = str(uuid.uuid1())   
        path = os.path.join(self.store.get_storage_directory(),location,uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path,"doc."+kind.lower())
        self.touch(p)
        if os.path.exists(p):
            self.store.index_doc(uid,name,location,kind)

        # make this the current document
        yew.store.put_user_pref('yewser','current_doc',uid)

        return self.store.get_doc(uid)

@click.group()
@click.option('--user', help="User name", required=False)
def cli(user):
    pass

@cli.command()
@click.argument('name', required=False)
@click.option('--location', help="Location endpoint alias for document", required=False)
@click.option('--kind', help="Type of document, txt, md, rst, json, etc.", required=False)
def create(name,location,kind):
    """Create a new document."""
    if not name:
        docs = yew.store.search_names("%s")
        for index,doc in enumerate(docs):
            click.echo("%s [%s]" % (doc.name,doc.kind))

        sys.exit(0)

    # get the type of file
    kind_tmp = yew.store.get_user_pref(yew.username,"default_doc_type")
    if kind_tmp and not kind:
        kind = kind_tmp

    if not location:
        location = 'deafult'

    doc = yew.create_document(name,location,kind)

    click.echo("created document: %s" % doc.uid)
    click.edit(editor='emacs', require_save=True, filename=doc.path)
    yew.store.post_doc(yew.store.get_doc(doc.uid))


def get_user_email():
    """Get user email from prefs or stdin."""
    self.url = self.store.get_user_pref(self.username,'url')


@cli.command()
@click.argument('name', required=False)
@click.argument('value', required=False)
def global_pref(name,value):
    """Show or set global preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    if not name:
        prefs = yew.store.get_globals()
        for pref in prefs:
            click.echo("%s = %s" % (pref))
    elif value:
        # we are setting a value on the name
        yew.store.put_global(name,value)
    else:
        click.echo("%s = %s" % (name,yew.store.get_global(name)))

@cli.command()
@click.argument('name', required=False)
@click.argument('value', required=False)
def user_pref(name,value):
    """Show or set global preferences.

    No name for a preference will show all preferences.
    Providing a value will set to that value.

    """
    # get user first of all
    username = yew.store.get_global('username')
    if not name:
        for k in YewStore.user_preferences:
            v = yew.store.get_user_pref(username,k)
            click.echo("%s = %s" % (k,v))
    elif value:
        # set the user preference
        yew.store.put_user_pref(username,name,value)
    else:
        click.echo("%s = %s" % (name,yew.store.get_user_pref(username,name)))

def document_menu(docs):
    """Show list of docs. Return selection."""
    for index,doc in enumerate(docs):
        click.echo("%s) %s" % (index,doc.name))
    v = click.prompt('Select document', type=int)
    if not v in range(len(docs)):
        print "Choice not in range"
        sys.exit(1)
    return docs[v]

def get_document_selection(name,list_docs):
    """Present lists or whatever to get doc choice."""

    if not name and not list_docs:
        #uid = yew.store.get_user_pref('yewser','current_doc')
        docs = yew.store.get_recent('yewser')
        for index,doc in enumerate(docs):
            click.echo("%s) %s" % (index,doc.name))
        v = click.prompt('Select document', type=int)
        if not v in range(len(docs)):
            print "Choice not in range"
            sys.exit(1)
        doc = docs[v]
    elif list_docs:
        docs = yew.store.get_docs()
        if len(docs) == 1:
            return docs[0]
        doc = document_menu(docs)
    elif name:
        docs = yew.store.search_names(name)
        if len(docs) == 1:
            return docs[0]
        doc = document_menu(docs)
    return doc
    
@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
@click.option('--open_file','-o',is_flag=True, required=False, help="Open the file in your host operating system.")
def edit(name,list_docs,open_file):
    """Edit a document."""

    doc = get_document_selection(name,list_docs)

    if open_file: 
        # send to host os to ask it how to open file
        click.launch(doc.get_path())
    else:
        click.edit(editor='emacs', require_save=True, filename=doc.path)


    yew.store.post_doc(yew.store.get_doc(doc.uid))
    yew.store.put_user_pref('yewser', 'current_doc', doc.uid)
    yew.store.update_recent('yewser', doc)

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
@click.option('--force','-f',is_flag=True, required=False)
@click.option('--remote','-r',is_flag=True, required=False)
def delete(name,list_docs,force,remote):
    """Delete a document."""

    doc = get_document_selection(name,list_docs)

    if force or click.confirm('Do you want to continue to delete the document?'):
        yew.store.delete_document(doc, local_only = not remote)


@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
@click.option('--remote','-r',is_flag=True, required=False)
def cat(name,list_docs,remote):
    """Send contents of document to stdout."""

    doc = get_document_selection(name,list_docs)
    if remote:
        r = yew.get("fetch",{"uid":doc.uid})
        remote_doc = json.loads(r.content)
        if remote_doc:
            click.echo(remote_doc['content'])
    else:
        click.echo(doc.get_content())

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
@click.option('--remote','-r',is_flag=True, required=False)
def show(name,list_docs,remote):
    """Show document details."""

    doc = get_document_selection(name,list_docs)
    doc.dump()
    if remote:
        r = yew.get("exists",{"uid":doc.uid})
        r_info = json.loads(r.content)
        click.echo("Remote: ")
        for k,v in r_info.items():
            click.echo("%s: %s" % (k,v))
        if not r_info['digest'] == doc.digest:
            click.echo("Docs are different")
            sdt = dateutil.parser.parse(r_info['date_updated'])
            server_newer = sdt > doc.get_last_updated_utc()
            click.echo("Server newer ? %s" % server_newer)

@cli.command()
def push():
    """Push all documents to the server."""

    docs = yew.store.get_docs()
    for doc in docs:
        click.echo("pushing: %s" % doc.name)
        yew.store.post_doc(doc)
    click.echo("Done!")

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
def head(name,list_docs):
    """Send start of document to stdout."""

    doc = get_document_selection(name,list_docs)
    click.echo(doc.get_content()[:250])

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
def tail(name,list_docs):
    """Send end of document to stdout."""

    doc = get_document_selection(name,list_docs)
    click.echo(doc.get_content()[-250:])

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
def rename(name,list_docs):
    """Send contents of document to stdout."""

    doc = get_document_selection(name,list_docs)
    click.echo("Rename: '%s'" % doc.name)
    v = click.prompt('Enter the new document title ', type=unicode)
    if v:
        doc = yew.store.rename_doc(doc,v)
    yew.store.post_doc(doc)

@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',is_flag=True, required=False)
def kind(name,list_docs):
    """Change kind of document."""

    doc = get_document_selection(name,list_docs)
    click.echo(doc)
    click.echo("Current document kind: '%s'" % doc.kind)
    for i,d in enumerate(yew.store.doc_kinds):
        click.echo("%s) %s" % (i,d))
    v = click.prompt('Select the new document kind ', type=int)
    if v == 0 or v in range(len(yew.store.doc_kinds)):
        kind = yew.store.doc_kinds[v]
        print "Changing document kind to: ", kind
        doc = yew.store.change_doc_kind(doc,kind)
    yew.store.post_doc(doc)

@cli.command()
def ping():
    """Ping server."""
    r = yew.ping()
    if r.status_code == 200:
        print json.loads(r.content)
        sdt = dateutil.parser.parse(json.loads(r.content))
        click.echo("Server time: %s" % sdt)
        print "Skew: ", datetime.datetime.now() - sdt
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)

@cli.command()
def api():
    """Get API of the server."""
    r = yew.api()
    if r.status_code == 200:
        # content should be server time
        print r.content
        sys.exit(0)
    click.echo("ERROR HTTP code: %s" % r.status_code)

if __name__ == '__main__':
    yew = YewCLI()
    cli()

        

