Exporting Documents
===================

You can create MS Word, PDF, HTML or other types of documents from your
text documents.

::

   yd convert foo docx

will create a file in the current directory called: ‘foo.docx’.

It supports whatever pandoc supports. Type:

::

   yd convert 

To see a list of supported formats.

For PDF, you’ll need to also install pdflatext in addition to pandoc:

https://www.latex-project.org/get/

On macos:

::

   brew cask install mactex

