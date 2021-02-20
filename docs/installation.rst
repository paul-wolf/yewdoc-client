Installation
============

Yewdocs works with Python >= 3.6

Make sure you have Python3 installed. Make sure you have pip3 working.

pandoc must be installed following the instructions specific to your
operating system.

MacOS:

:: shell

   brew install pandoc

Ubuntu:

:: shell

   sudo apt-get install pandoc

Windows:

::

   http://pandoc.org/installing.html

Git clone the repo:

::

   git clone git@github.com:paul-wolf/yewdoc-client.git

cd into the resulting directory and execute the install command:

::

   cd yewdoc-client
   pip3 install --editable .

That should be all that is required. We will later make a PyPi module
available. Now type:

::

   yd info

You should see output about settings.
