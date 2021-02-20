Some Technical Details
======================

The files are all kept in a directory: ``~/.yew.d/``. Assume we have a
username of ``yewser``:

::

   ~/yew.d/yewser/default/

``default`` in this example refers to the “location”. This is hard-coded
at this time, but in future will support different remote settings.

under ``default`` are all the document directories, one directory per
document. Each document directory has the document with the appropriate
text extension. There might be a media subdirectory if you have attached
files to the document, ``yd attach <filepath>``. In addition, there
could be a file for holding tags associated with the document
``__tags.json``.

in the yewdoc user directory, ``~/yew.d/yewser`` in our example, there
are at least two files:

-  index.json: an index of all the documents and tags

-  settings.json: user preferences

The index.json is kept up to date whenever the user makes changes to
documents, create, edit, tag, delete, etc. If this is corrupted somehow,
it can be regenerated:

::

   yd generate-index

This command can be invoked any time and the index.json will be replaced
with a accurate version. settings.json however will need to be created
from scratch however if it is deleted or lost. Add things to it with the
``user-pref`` command:

::

   yd user-pref <name> <value>

Check preferences:

::

   yd user-pref

Most of these settings are set via the ``yd configure`` command. But you
can change them via the ``user-pref`` command more directly:

::

   yd user-pref location.default.first_name Paul

Will change the first_name to Paul. These are generally only used to
configure a remote.

