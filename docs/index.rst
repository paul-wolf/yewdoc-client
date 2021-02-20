Welcome to yewdocs's documentation!
===================================

Yewdocs is a personal document manager that makes creating and editing
text documents from the command line easier than using only an editor
and filesystem commands.

Yewdocs is for *text* documents: plain text, restructuredText, markdown,
conf, etc. It offers these features:

-  Filesystem transparency: the user doesn’t need to know where files
   are stored.

-  Entirely keyboard driven.

-  Tags: define tags and organise your documents with them.

-  Familiar commands: yewdocs has commands like ‘ls’, ‘head’, ‘tail’,
   that are familiar to most shell users.

-  Optional cloud storage for synchronising to multiple
   devices/workstations.

-  Document conversions: it will generate any format that pandoc is able
   to convert to/from. There is special support for generation of html
   and the use of templates.

-  Integration with other command line utilities: as just another shell
   utility, you can do normal shell piping in and out, grep, etc.

Think of it as a command line note taking application.

The target users are those who prefer to work on the command line
without the overhead of switching back and forth between a shell and the
host OS GUI. When working regularly on the command line, it is a
considerable annoyance to have to break out to use the host OS file
management app to find files and use the mouse. Yewdocs lets the user
seamlessly browse and operate on her collection of text files. These can
be snippets, larger documents, notes, etc. Exporting to other formats is
easy and natural.

A major design goal is to reduce the mental overhead of finding files.
Once a file is managed by Yewdocs, it is easy to perform operations like
editing it without needing to remember the exact name or location.
Documents can be managed by Yewdocs either within its own repository or
in-place as linked documents.

You are not forced to choose between your favourite non-text editor and
shell editor. You can just as well use Sublime, Atom or other
non-console interfaces for editing Yewdocs documents.

It’s possible to maintain text documents on a server and sync to any
local device that supports Python (>= 3.6) and one of the common \*nix
shells.

You can edit and manage any kind of text file, txt, rst, md, conf, etc.
Yewdocs does have a slight prejudice towards Markdown for newly created
documents but you can easily specify any format you wish or convert a
file to another format after creating it.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   specify
   tags
   backups
   export
   browse
   users
   remote
   technical
   commands
   development

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
