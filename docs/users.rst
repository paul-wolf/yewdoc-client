Users and Configuration
=======================

Yewdocs implements its own users. These are not the same as either the
local system user nor the remote Yewdocs user. In ``~/.yew.d/`` you’ll
find one or more user names. You can setup new users any time with the
``--user`` parameter that comes right after ``yd``:

::

   yd --user paul ls -l

Use this immediately after ``yd`` and the command will use that user
context. Yewdocs tries to get the user via several means:

-  user the current operating system user

-  check for ``--user``

-  check for environment: YEWDOC_USER

-  check for a config file called ``~/.yew`` that has this:

   [Yewdoc] username = yewser

where ``yewser`` is the desired username.
