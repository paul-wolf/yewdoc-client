YEWDOC
======

Yewdoc is a document editor that makes creating and editing text documents from the command line easier. 

It should be emphasised that it's for *text* documents: plain text, restructuredtext, markdown, etc. It offers these features:

* Filesystem transparency: the user doesn't need to know where files are stored. 
* Familiar commands: yewdoc has commands like 'ls', 'cat', 'head', 'tail', that are familiar to most shell users.
* Cloud storage for synchronising to multiple devices/workstations. 
* Document conversions: it will generate any format that pandoc is able to convert to/from. There is special support for generation of html and the use of templates. 
* Supports attachments: it supports attaching any file types but in particular graphics files that might be referenced in-line. 
* Integration with other command line utilities: you can do normal shell piping in and out, grep, etc. 
 
You might think of it as a personal wiki, though the capabilities go beyond that. The target users are those who prefer to work in a single context, such as command-line without the mental overhead of switching back and forth between a shell and the host OS GUI. When working regularly on the command line, it is a considerable annoyance to have to break out to use the host OS file management app to find files and use the mouse. Yewdoc lets the user seamlessly browse and operate on her collection of text files. These can be larger documents, notes, etc. Exporting to other formats is a easy and natural. 

It's possilbe to maintain text documents on a server and sync to any local device that supports Python (> 2.7) and one of the common *nix shells. 

Create a new file and start editing: 

    yd create "My new text file"

Yewdoc uses the EDITOR environment to determine what editor to launch. You can also have yewdoc launch an editor from the host OS and let it decide which application handles that file type. This might be Atom, Sublime Text or whatever editor you choose to associate with the file type. 

Edit the file we just created:

    yd edit my

You don't have to provide the whole title of the document. If the fragment, in this case "my", matches case-insensitively to a document, it will be loaded in the editor. Otherwise, the user is presented with a choice of all matching files. 

    yd show my

will dump the contents of "My new text file" to stdout. Create a new document now from stdin:

    yd read "The next big thing"

Type some content and enter end of file (ctrl-D usually). 

Copy a document: 

    yd show my | yd read "the next"

You will be prompted that the file exists and do you want to start a new file, append to the existing file, etc. 

Configuration
=============

No configuration is necessary to work locally without mirroring changes to the cloud (to a server through an internet connection). If you want to have changes saved remotely, you need to provide certain information, like:

* Email: your email that has not been registered to Remote
* URL: the endpoint for the remote yewdoc service. Currently, that is just https://doc.yew.io
* username: this is the username you desire to have on the remote service
* first name: first name (optional)
* last name: your last name (optional)

You can enter this via the `configure` command: 

    yd configure

Or immediately attempt to register: 

    yd register

In both cases, yewdoc will collect the required information from you. 

In the case that a registration succeeds, you will have set a token that forthwith enables transparent access to the remote server. The token is secret and should be protected. 

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

```
$ yd
Usage: yd [OPTIONS] COMMAND [ARGS]...

Options:
  --user TEXT  User name
  --help       Show this message and exit.

Commands:
  api          Get API of the server.
  attach       Take a file and put into media folder.
  browse       Convert to html and attempt to load in web...
  show         Send contents of document to stdout.
  configure    Get configuration information from user.
  convert      Convert to destination_format and print to...
  create       Create a new document.
  delete       Delete a document.
  edit         Edit a document.
  global_pref  Show or set global preferences.
  head         Send start of document to stdout.
  kind         Change kind of document.
  ls           List documents.
  ping         Ping server.
  push         Push all documents to the server.
  register     Try to get a user account on remote.
  rename       Send contents of document to stdout.
  describe     Show document details.
  sync         Pushes local docs and pulls docs from remote.
  tail         Send end of document to stdout.
  take         Create a document from a file.
  user_pref    Show or set global preferences.
```


