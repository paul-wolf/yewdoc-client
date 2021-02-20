Usage
=====

Create a new document and start editing:

::

   yd create foo

Yewdocs uses the EDITOR environment to determine what editor to launch.
You can also have Yewdocs launch an editor from the host OS and let it
decide which application handles that file type. This might be Atom,
Sublime Text or whatever editor you choose to associate with the file
type depending on your OS.

Edit the file we just created:

::

   yd edit foo

Edit the file with Sublime or whatever you have specified in your host
OS to handle this type of file:

::

   yd edit -o foo

You don’t have to provide the whole title of the document. If the
fragment, in this case “foo”, matches case-insensitively to a document,
it will be loaded in the editor. Otherwise, the user is presented with a
choice of all matching files.

::

   yd show foo

will dump the contents of “foo” to stdout. Create a new document now
from stdin:

::

   yd read bar

Type some content and enter end of file (ctrl-d usually).

Copy a document to a new one:

::

   yd show foo | yd read --create bar

A copy of the contents of foo will appear in a new document, bar.

List all your documents:

::

   yd ls

Sync your documents to/from a Yewdocs server:

::

   yd sync

You must have previously registered with the Yewdocs server. This is
entirely optional. It will also sync tags and document/tag associations.
See below under Configuration.

You can symbolically link a file:

::

   yd take ~/.tmux.conf --symlink

the file ``.tmux.conf`` will become a managed document but any
operations on the file will modify the file in-place. This can be very
convenient because you don’t have to remember the exact name or location
of the tmux file to edit it:

::

   yd edit tmux

But, of course, great care must be taken to not forget that you are not
working on a copy but the file itself.

We don’t sync from remote to a symlinked file. That means, local
symlinked files will not be overwritten from remote. This is to prevent
unintential changes to local files.
