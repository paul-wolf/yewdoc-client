YEWDOCS
=======

[![Build Status](https://travis-ci.org/paul-wolf/yewdoc-client.svg?branch=master)](https://travis-ci.org/paul-wolf/yewdoc-client)

Yewdocs is a personal document manager that makes creating and editing
text documents from the command line easier than using only an editor
and filesystem commands.

Yewdocs is for *text* documents: plain text, restructuredText,
markdown, conf, etc. It offers these features:

* Filesystem transparency: the user doesn't need to know where files
  are stored.

* Entirely keyboard driven.

* Tags: define tags and organise your documents with them.

* Familiar commands: yewdocs has commands like 'ls', 'head', 'tail',
  that are familiar to most shell users.
  
* Optional cloud storage for synchronising to multiple
  devices/workstations.

* Document conversions: it will generate any format that pandoc is
  able to convert to/from. There is special support for generation of
  html and the use of templates.
  
* Integration with other command line utilities: as just another shell
  utility, you can do normal shell piping in and out, grep, etc.

* GPG encryption: documents can be easily encrypted/decrypted.

The target users are those who prefer to work on the command line
without the overhead of switching back and forth between a shell and
the host OS GUI. When working regularly on the command line, it is a
considerable annoyance to have to break out to use the host OS file
management app to find files and use the mouse. Yewdocs lets the user
seamlessly browse and operate on her collection of text files. These
can be snippets, larger documents, notes, etc. Exporting to other
formats is easy and natural.

A major design goal is to reduce the mental overhead of finding
files. Once a file is managed by Yewdocs, it is easy to perform
operations like editing it without needing to remember the exact name
or location. Documents can be managed by Yewdocs either within its own
repository or in-place as linked documents.

You are not forced to choose between your favourite non-text editor
and shell editor. You can just as well use Sublime, Atom or other
non-console interfaces for editing Yewdocs documents.

It's possible to maintain text documents on a server and sync to any
local device that supports Python (>= 3.4) and one of the common *nix
shells.

You can edit and manage any kind of text file, txt, rst, md, conf,
etc. Yewdocs does have a slight prejudice towards Markdown for newly
created documents but you can easily specify any format you wish or
convert a file to another format after creating it.

Installation
============

Yewdocs works with Python >= 3.4

Make sure you have Python3 installed. Make sure you have pip3 working. 

pandoc must be installed following the instructions specific to your
operating system.

MacOS:

    brew install pandoc

Ubuntu:

    sudo apt-get install pandoc

Windows:

    http://pandoc.org/installing.html

Git clone the repo:

    git clone git@github.com:paul-wolf/yewdoc-client.git

cd into the resulting directory and execute the install command:

    cd yewdoc-client
    pip3 install --editable .

That should be all that is required. We will later make a PyPi module
available. Now type:

    yd info

You should see output about settings.

Usage
=====

Create a new document and start editing: 

    yd create foo

Yewdocs uses the EDITOR environment to determine what editor to
launch. You can also have Yewdocs launch an editor from the host OS and
let it decide which application handles that file type. This might be
Atom, Sublime Text or whatever editor you choose to associate with the
file type depending on your OS.

Edit the file we just created:

    yd edit foo

Edit the file with Sublime or whatever you have specified in your host
OS to handle this type of file:

    yd edit -o foo

You don't have to provide the whole title of the document. If the
fragment, in this case "foo", matches case-insensitively to a document,
it will be loaded in the editor. Otherwise, the user is presented with
a choice of all matching files.

    yd show foo

will dump the contents of "foo" to stdout. Create a new document now from stdin:

    yd read bar

Type some content and enter end of file (ctrl-d usually). 

Copy a document to a new one: 

    yd show foo | yd read --create bar

A copy of the contents of foo will appear in a new document, bar. 

List all your documents: 

    yd ls

List all documents on the server (if you are using the Yewdocs server):

    yd ls -r

Sync your documents to/from a Yewdocs server:

    yd sync

You must have previously registered with the Yewdocs server. This is
entirely optional. It will also sync tags and document/tag
associations. See below under Configuration.

You can symbolically link a file:

    yd take ~/.tmux.conf --symlink

the file `.tmux.conf` will become a managed document but any
operations on the file will modify the file in-place. This can be very
convenient because you don't have to remember the exact name or
location of the tmux file to edit it:

    yd edit tmux

But, of course, great care must be taken to not forget that you are
not working on a copy but the file itself.


Tags
====

You can create tags and associate them with documents for making file
organisation and publishing easier.

Create a tag:

    yd tag -c red

Assign the 'red' tag to the doc 'foo':

    yd tag red foo

List documents with the red tag in long format, humanized:

    yd ls -lh -t red

Dissociate the tag 'red' from the document 'foo':

    yd tag -u red foo

How many documents with the foo tag:

    yd ls -t foo | wc

List all tags:

    yd tag


Specifying Documents
====================

All the commands that operate on one or more documents will take as a
name one of the following:

* Document title (or case-insensitive sub-string of the title)

* Document id (a UUID)

* Short document id (first 8 characters of full id)

The document id is a UUID that looks something like this:

    3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa

The short document id is therefore `3ccc3fcc`. I can use the
`describe` command to get full information about this document:

```
➜  yd describe 3ccc3fcc
uid      : 3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa
link     : False
title    : Project Management
location : default
kind     : md
size     : 1563
digest   : 0899f1728b9b653f8477a64b6fa5f750b87bd2a77a716dfe0eeeb91ae90b8fc4
path     : /Users/paul/.yew.d/yewser/default/3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa/doc.md
Last modified: 2015-09-16 19:07:16+00:00
```

I can also use a part of the title:

    yd describe project

If more than one title has the string `project`, it will provide a list to choose from.

Or use the full id:

    yd describe 3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa


Local Web Browser
=================

You can view a set of documents associated with a tag or tags in a web browser:

    yd browse -t blog

This will try to convert all documents tagged with 'blog' to html and
load them in the default browser. The default

    yd browse my_template.j2 -t blog

where `my_template.j2` is a Jinja template
(http://jinja.pocoo.org/). Without this the default template is
used. This has a left sidebar for navigating documents.

Encryption
==========

Encrypt a document:

    yd encrypt foo

Decrypt a document:

    yd decrypt foo

If you have remote cloud storage activated, the encrypted document is
sent to the remote. Check all encrypted documents:

    yd ls -l --encrypted
    ee608edc      md          569   2019-02-17 09:49:55 (E)test
    19128186      md          561   2019-02-17 10:03:20 (E)foo

Note the `(E)` indicating the document is encrypted. Some notes about this feature:

* Your gpg home directory defaults to `.gnupg`. Use the --gpghome
  option to change it. The specification of the home directory is only
  good for the one invocation. You would need to provide it again
  while decrypting.

* The key identity is chosen by your registered email. Therefore, this
  might not work if you are not registered with the remote cloud
  server. Just set this manually:

    yd user-pref location.default.email joe.bloggs@whatever.com

The email must be one used for generating a key in your default or
specified gnupg directory.

* We pass the encryption/decryption commands to gpg without
  regard to what kind of keys you have (length, encryption standard,
  etc.)

* When a document is encrypted, it is done in-place. So, locally,
  there is no longer an unencrypted version. This means if you lose
  the keys, you won't be able to access the encrypted content. If you
  are on the remote cloud server, the encrypted file will be there but
  likewise will be permanently encrypted in this case.

* Obviously, there is no way to view the unencrypted file via the web
  site (if you use that) as keys are never touched in any way other
  than to carry out local encryption/decryption operations.

* If you use the remote service and you have made changes in the past,
  your history on the remote service may still contain unencrypted
  history of changes.

If you want to see what keys will be used for encryption:

    yd info

This will output some generally useful information but also
information about which keys will be used. Currently, it will assume
`.gnupg` as home directory.

The current implementation is very simple and lacks some desirable
refinements, like unencrypting for you when when you want to edit the
document. Currently, you need to manually do this before editing
yourself. Also, we should store the home directory for .gnupg instead
of assuming the default in some cases. Such enhancements are on the
way.

Overview of Commands
====================

For local files the following commands are available:

```
attach       Take a file and put into media folder.
browse       Convert to html and attempt to load in web...
context      Set or unset a tag context filter for listings.
convert      Convert to destination_format and print to...
create       Create a new document.
decrypt       Decrypt a document.
delete       Delete a document.
describe     Show document details.
diff         Compare two documents.
edit         Edit a document.
encrypt      Encrypt a document.
find         Search for spec in contents of docs.
global_pref  Show or set global preferences.
head         Send start of document to stdout.
kind         Change kind of document.
ls           List documents.
read         Get input from stdin and either create a new...
rename       Rename a document.
show         Send contents of document to stdout.
status       Print info about current setup.
tag          Manage tags.
tail         Send end of document to stdout.
take         Import a file as a document.
user_pref    Show or set global preferences.
```

Remote commands:

```
authenticate Authenticate with remote and get token.
configure    Get configuration information from user.
ping         Ping server.
push         Push all documents to the server.
register     Try to get a user account on remote.
sync         Pushes local docs and pulls docs from remote.
api          Get API of the server.
```


Yewdocs Server Configuration
===========================

No configuration is necessary to work locally without mirroring
changes to the cloud (to a server through an internet connection):

<https://doc.yew.io>

If you want to have changes saved remotely, you need to provide
certain information, like:

* Email: your email that has not been registered to Remote
* URL: the endpoint for the remote Yewdocs service. Currently, that is just https://doc.yew.io
* username: this is the username you desire to have on the remote service
* first name: first name (optional)
* last name: your last name (optional)

There are three commands:

* yd configure: get information used to configure remote communication
* yd register: get a new user account with the remote service
* yd authenticate: authenticate with remote when you already have an account

In the case that a registration succeeds, you will have set a token
that forthwith enables transparent access to the remote server. The
token is secret and should be protected. It's located in your home
directory in an sqlite database table.

You can check all user preferences via the `user-pref` command:

```
$ yd user-pref
location.default.url = https://doc.yew.io
location.default.email = paul.wolf@yewleaf.com
location.default.username = yewser
location.default.password = None
location.default.first_name = Paul
location.default.last_name = Wolf
location.default.token = fe0be94826b451bba72j54tjnwlr2jrn2o5cd9b
```


