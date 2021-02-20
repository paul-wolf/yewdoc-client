Specifying Documents
====================

All the commands that operate on one or more documents will take as a
name one of the following:

-  Document title (or case-insensitive sub-string of the title)

-  Document id (a UUID)

-  Short document id (first 8 characters of full id)

The document id is a UUID that looks something like this:

::

   3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa

The short document id is therefore ``3ccc3fcc``. I can use the
``describe`` command to get full information about this document:

::

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

I can also use a part of the title:

::

   yd describe project

If more than one title has the string ``project``, it will provide a
list to choose from.

Use the id to be very exact:

::

   yd describe 3ccc3fcc-5acc-11e5-b07d-ac87a33b7daa

or the short id:

::

   yd describe 3ccc3fcc

