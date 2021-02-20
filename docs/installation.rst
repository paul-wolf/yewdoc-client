Installation
============

Yewdocs works with Python >= 3.8

Make sure you have Python3 installed. Make sure you have pip3 working.

You can user yewdocs without `Pandoc <https://pandoc.org/>`_, but some nice features will be missing like
converting documents to other types, pdf, html, docx, etc. Pandoc must be installed following the instructions specific to your
operating system.

MacOS:

::

   brew install pandoc

Ubuntu:

::

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

For PDF exports, you’ll need to also install `pdflatext
<https://www.latex-project.org/get/>`_ in addition to pandoc:

On macos:

::

   brew cask install mactex
