Encryption
==========

Encrypt a document:

    yd encrypt foo

Decrypt a document:

    yd decrypt foo

If you have remote cloud storage activated, the encrypted document is
sent to the remote. Check all encrypted documents:

    yd ls -l --encrypted
    ee608edc      md          569   2019-02-17 09:49:55 (E)test
    19128186      md          561   2019-02-17 10:03:20 (E)foo

Note the `(E)` indicating the document is encrypted. Some notes about this feature:

* Your gpg home directory defaults to `.gnupg`. Use the --gpghome
  option to change it. The specification of the home directory is only
  good for the one invocation. You would need to provide it again
  while decrypting.

* The key identity is chosen by your registered email. Therefore, this
  might not work if you are not registered with the remote cloud
  server. Just set this manually:

    yd user-pref location.default.email joe.bloggs@whatever.com

The email must be one used for generating a key in your default or
specified gnupg directory.

* We pass the encryption/decryption commands to gpg without
  regard to what kind of keys you have (length, encryption standard,
  etc.)

* Only the contents are encrypted. Title, tags and some other meta
  data are not encrypted.

* When a document is encrypted, it is done in-place. So, locally,
  there is no longer an unencrypted version. This means if you lose
  the keys, you won't be able to access the encrypted content. If you
  are on the remote cloud server, the encrypted file will be there but
  likewise will be permanently encrypted in this case.

* Obviously, there is no way to view the unencrypted file via the web
  site (if you use that) as keys are never touched in any way other
  than to carry out local encryption/decryption operations.

* If you use the remote service and you have made changes in the past,
  your history of changes on the remote service will be deleted for a
  document that you encrypt locally. This is to prevent unintentially
  leaving unencrypted information on the remote that you think is not
  available.

* If you call the decrypt operation on an encrypted file, it encrypts
  it again. You'll need to decrypt twice (as many times as you
  encrypted) to get the original content back.

If you want to see what keys will be used for encryption:

    yd info

This will output some generally useful information but also
information about which keys will be used. Currently, it will assume
`.gnupg` as home directory.

To use encryption safely, you need to be aware of numerous things that
are out of scope for this document and Yewdocs, like safe key
generation and safe key storage. Encrypting a file in-place is not a
guarantee that a technical forensic operation could not possibly
retrieve unencrypted content with possession of the host. Yewdocs
assumes here that the encrypted documents are on the same filesystems
as your keys. Are your keys protected by a passphrase? Is it reallly
safe to have keys in the same place as encrypted data? All of these
issues are the user's responsibility.
