Tags
====

You can create tags and associate them with documents for making file
organisation and publishing easier.

Assign the ‘red’ tag to the doc ‘foo’:

::

   yd tag red foo

List documents with the red tag in long format, humanized:

::

   yd ls -lh -t red

Dissociate the tag ‘red’ from the document ‘foo’:

::

   yd tag -u red foo

How many documents with the foo tag:

::

   yd ls -t foo | wc

List all tags:

::

   yd tags
