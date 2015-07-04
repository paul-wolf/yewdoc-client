import os
import sys
import uuid
import traceback
from os.path import expanduser
import click
import sqlite3
import requests
from requests.auth import HTTPBasicAuth
from strgen import StringGenerator as SG
import json

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

class Document(object):
    """Describes a document."""
    def __init__(self,store,uid,name,location,kind):
        self.uid = uid
        self.name = name
        self.location = location
        self.kind = kind
        self.path = os.path.join(store.get_storage_directory(),location,uid,"doc."+kind)
        if not os.path.exists(self.path):
            raise Exception("Non-existant document: %s" % self.path)

    def serialize(self, no_uid=False):
        """Serialize as json to send to server."""
        data = {}
        data['uid'] = self.uid
        data['parent'] = None
        data['title'] = self.name
        data['kind'] = self.kind
        data['content'] = open(self.path).read()

        return json.dumps(data)

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
        "current_doc",
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
        c.execute('''CREATE TABLE IF NOT EXISTS document (uid,name,location,kind)''')
        conn.commit()
        return conn

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
        print "put_user_pref (%s,%s,%s): "% (username,k,v)
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
        print self.get_user_pref(username,k)

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

    def index_doc(self, uid, name, location=None, kind="txt"):
        """Enter document into db."""
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

    def post_doc(self,doc):
        """Serialize and send document.
        
        This will create the document on the server unless it exists.
        If it exists, it will be updated. 

        """
        username = self.get_global('username')
        location_url = self.get_user_pref(username,'yewdoc_url.default')
        yewdoc_token = "Token %s" % self.get_user_pref(username,'yewdoc_token')
        data = doc.serialize()
        headers = {'Authorization': yewdoc_token, "Content-Type":"application/json"}
        #url = "%s/api/documents/%s" % (location_url,doc.uid)
        url = "%s/api/document/" % location_url
        r = requests.post(url, data=data, headers=headers, verify=False)
        if r.status_code == 400:
            # it exists, so let's put together the  update url and PUT it
            url = "%s/api/document/%s/" % (location_url,doc.uid)
            data = doc.serialize(no_uid=True)
            r = requests.put(url, data=data, headers=headers, verify=False)
        

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


    def status(self):
        """Print status."""
        print "url: ", self.url
        print "username: ", self.username
        print "project: ", self.project
        print "card: ", self.card

    def touch(self,path):
        with open(path, 'a'):
            os.utime(path, None)
    
    def create_document(self,name,location=None,kind="txt"):
        if not location:
            location = self.location
        uid = str(uuid.uuid1())   
        path = os.path.join(self.store.get_storage_directory(),location,uid)
        if not os.path.exists(path):
            os.makedirs(path)
        p = os.path.join(path,"doc."+kind.lower())
        self.touch(p)
        if os.path.exists(p):
            self.store.index_doc(uid,name,location)

        print "PUTTING THIS IN CURRENT: ", uid
        yew.store.put_user_pref('yewser','current_doc',uid)

        return self.store.get_doc(uid)

@click.group()
@click.option('--user', help="User name", required=False)
def cli(user):
    pass

@cli.command()
@click.argument('name', required=False)
@click.option('--location', help="Location endpoint alias for document", required=False)
@click.option('--kind', default='txt', help="Type of document, txt, md, rst, json, etc.", required=False)
def doc(name,location,kind="txt"):
    """Create a new document."""
    if not name:
        docs = yew.store.search_names("%s")
        for index,doc in enumerate(docs):
            click.echo("%s: %s" % (doc.uid,doc.name))
        sys.exit(0)

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
    
@cli.command()
@click.argument('name', required=False)
@click.option('--list_docs','-l',required=False)
def edit(name,list_docs):
    """Edit a document."""

    if not name:
        uid = yew.store.get_user_pref('yewser','current_doc')
        doc = yew.store.get_doc(uid)
        print doc
    else:
        docs = yew.store.search_names(name)
        for index,doc in enumerate(docs):
            click.echo("%s) %s" % (index,doc.name))
        v = click.prompt('Select document to edit', type=int)
        if not v in range(len(docs)):
            print "Choice not in range"
            sys.exit(1)
        doc = docs[v]

    click.edit(editor='emacs', require_save=True, filename=doc.path)

    yew.store.post_doc(yew.store.get_doc(doc.uid))

@cli.command()
def status():
    """Show status."""
    yew.status()
    

if __name__ == '__main__':
    yew = YewCLI()
    cli()

        

