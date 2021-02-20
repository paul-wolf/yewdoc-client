Documents in Browser
====================

You can view a set of documents associated with a tag or tags in a web
browser:

::

   yd browse -t blog

This will try to convert all documents tagged with ‘blog’ to html and
load them in the default browser. The default

::

   yd browse my_template.j2 -t blog

where ``my_template.j2`` is a Jinja template (http://jinja.pocoo.org/).
Without this the default template is used. This has a left sidebar for
navigating documents.
