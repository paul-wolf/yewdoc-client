
Yewdocs Server Configuration
============================

No configuration is necessary to work locally without mirroring changes
to the cloud (to a server through an internet connection):

https://doc.yew.io

If you want to have changes saved remotely, you need to provide certain
information, like:

-  Email: your email that has not been registered to Remote
-  URL: the endpoint for the remote Yewdocs service. Currently, that is
   just https://doc.yew.io
-  username: this is the username you desire to have on the remote
   service
-  first name: first name (optional)
-  last name: your last name (optional)

There are three commands:

-  yd configure: get information used to configure remote communication
-  yd register: get a new user account with the remote service
-  yd authenticate: authenticate with remote when you already have an
   account

In the case that a registration succeeds, you will have set a token that
forthwith enables transparent access to the remote server. The token is
secret and should be protected. It’s located in your home directory in
an sqlite database table.

You can check all user preferences via the ``user-pref`` command:

::

   $ yd user-pref
   location.default.url = https://doc.yew.io
   location.default.email = paul.wolf@yewleaf.com
   location.default.username = yewser
   location.default.password = None
   location.default.first_name = Paul
   location.default.last_name = Wolf
   location.default.token = fe0be94826b451bba72j54tjnwlr2jrn2o5cd9b


.. |Build Status| image:: https://travis-ci.org/paul-wolf/yewdoc-client.svg?branch=master
   :target: https://travis-ci.org/paul-wolf/yewdoc-client
