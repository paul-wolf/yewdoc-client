Using Different Remotes
=======================

You can sync your collection of documents to a remote backend to make
them available across different devices/workstations.

Two remotes are possible: Web and AWS S3 storage. You can add your own
remote backend, see ``remote`` directory for the source code.

For S3, you need an AWS account and access credentials. In the
~/.yew.d/settings.json you configure access to the remote.

.. code:: json

   {
       "location": {
           "default": {
               "remote_type": "RemoteS3",
               "aws_access_key_id": "XXXXXXXXXXXXXXXXXXXXXXXXXXX",
               "aws_secret_access_key": "YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
               "s3_bucket": "my-personal-bucket"
           }
       }
   }

The remote REST backend is configured something like this:

.. code:: json

   {
       "location": {
           "default": {
               "remote_type": "RemoteREST",
               "url": "https://doc.yew.io",
               "email": "paul.wolf@ripeco.com",
               "username": "paul",
               "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
               "first_name": "Blah",
               "last_name": "Wolf",
               "token": "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
           }
       }
   }
