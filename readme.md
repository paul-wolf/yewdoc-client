YEWDOC
======

Yewdoc is a personal document manager that makes creating and editing
text documents from the command line easier than using an editor and
filesystem commands.

Yewdoc is for *text* documents: plain text, restructuredText,
markdown, conf, etc. It offers these features:

* Filesystem transparency: the user doesn't need to know where files
  are stored.

* Entirely keyboard driven.

* Tags: you can tag documents with tags you define and filter by tag.

* Familiar commands: yewdoc has commands like 'ls', 'head', 'tail',
  that are familiar to most shell users.
  
* Optional cloud storage for synchronising to multiple
  devices/workstations.

* Document conversions: it will generate any format that pandoc is
  able to convert to/from. There is special support for generation of
  html and the use of templates.
  
* Integration with other command line utilities: as just another shell
  utility, you can do normal shell piping in and out, grep, etc.
 
The target users are those who prefer to work in a single context,
such as command-line without the mental overhead of switching back and
forth between a shell and the host OS GUI. When working regularly on
the command line, it is a considerable annoyance to have to break out
to use the host OS file management app to find files and use the
mouse. Yewdoc lets the user seamlessly browse and operate on her
collection of text files. These can be snippets, larger documents,
notes, etc. Exporting to other formats is easy and natural.

A major design goal is to reduce the mental overhead of finding
files. Once a file is managed by Yewdoc, it is very easy to perform
operations like editing on it without needing to remember the exact
name or location. Documents can managed by Yewdoc either within it's
own repositor or in-place as linked documents.

You are not forced to choose between your favourite non-text editor
and shell editor. You can just as well use Sublime, Atom or other
non-text interfaces for editing Yewdoc documents.

It's possible to maintain text documents on a server and sync to any
local device that supports Python (>= 2.7) and one of the common *nix
shells.

You can edit and manage any kind of text file, txt, rst, md, conf,
etc. Yewdoc does have a slight prejudice towards Markdown for newly
created documents but you can easily specify any format you wish.

> This project is at a somewhat early stage and therefore is subject
> to change.

Installation
============

Yewdoc works with Python 2.7. 

Git clone the repo, cd into the resulting directory and execute the
install command:

    ./install.sh

> Currently pandoc must be installed following the instructions specific
> to your operating system.

That should be all that is required. We will later make a PyPi module
available.

Usage
=====

Create a new document and start editing: 

    yd create foo

Yewdoc uses the EDITOR environment to determine what editor to
launch. You can also have yewdoc launch an editor from the host OS and
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

List all documents on the server (if you are using the Yewdoc server):

    yd ls -r

Sync your documents to/from a Yewdoc server:

    yd sync

You must have previously registered with the Yewdoc server. This is
entirely optional. It will also sync tags and document/tag
associations. See below under Configuration.

You can symbolically link a file:

    yd take ~/.tmux.conf

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


Yewdoc Server Configuration
===========================

No configuration is necessary to work locally without mirroring
changes to the cloud (to a server through an internet connection).

We have a cloud-based install of related project that can allow you to
manage a mirrored version of your text document repository with a web
interface. This is currently in an experimental mode and no guarantee
that it will work. This will be open-source when we have feel
confident that it's working properly. The location for this:

    https://doc.yew.io

If you want to have changes saved remotely, you need to provide
certain information, like:

* Email: your email that has not been registered to Remote
* URL: the endpoint for the remote yewdoc service. Currently, that is just https://doc.yew.io
* username: this is the username you desire to have on the remote service
* first name: first name (optional)
* last name: your last name (optional)

You can enter this via the `configure` command: 

    yd configure

Or immediately attempt to register: 
  
    yd register

In both cases, Yewdoc will collect the required information from you. 

In the case that a registration succeeds, you will have set a token
that forthwith enables transparent access to the remote server. The
token is secret and should be protected. It's located in your home
directory in an sqlite database table.

You can check all user preferences via the `user_pref` command:

```
$ yd user_pref
location.default.url = https://doc.yew.io
location.default.email = paul.wolf@yewleaf.com
location.default.username = yewser
location.default.password = None
location.default.first_name = Paul
location.default.last_name = Wolf
location.default.token = fe0be94826b451bba72j54tjnwlr2jrn2o5cd9b
```

