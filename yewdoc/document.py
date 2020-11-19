import os
import codecs

import click

from .utils import (
    bcolors,
    delete_directory,
    err,
    get_sha_digest,
    get_short_uid,
    is_binary_file,
    is_binary_string,
    is_short_uuid,
    is_uuid,
    modification_date,
    slugify,
    to_utc,
)

from . import file_system as fs

DOC_KINDS = ["md", "txt", "rst", "json"]

class Document(object):
    """Describes a document."""

    def __init__(self, store, uid, name, location, kind, encrypt, ipfs_hash):
        self.store = store
        self.uid = uid
        self.name = name
        self.location = location
        self.kind = kind
        self.path = os.path.join(
            store.yew_dir, store.location, uid, f"doc.{kind}"
        )
        # TODO: lazy load
        self.digest = self.get_digest()
        self.directory_path = os.path.join(store.yew_dir, store.location, uid)
        self.encrypt = encrypt


    def toggle_encrypted(self):
        """
        https://tools.ietf.org/html/rfc4880
        We should be safe and check the content.
        """
        c = self.store.conn.cursor()
        content_start = self.get_content()[:100].strip()
        encrypted = 1 if "BEGIN PGP MESSAGE" in content_start else 0
        sql = "UPDATE document SET encrypt = ? WHERE uid = ?"
        c.execute(sql, (encrypted, self.uid))
        # return boolean
        return encrypted == 1

    def check_encrypted(self):
        return self.get_content().startswith("-----BEGIN PGP MESSAGE-----")

    def is_encrypted(self):
        return self.encrypt == 1

    def short_uid(self):
        """Return first part of uuid."""
        return self.uid.split("-")[0]

    def get_safe_name(self):
        """Return safe name."""
        return slugify(self.name)

    def get_digest(self):
        return get_sha_digest(self.get_content())

    def get_basename(self):
        return "doc"

    def get_filename(self):
        return u"%s.%s" % (self.get_basename(), self.kind)

    def get_path(self):
        return os.path.join(
            self.store.yew_dir,
            self.store.location,
            self.uid,
            self.get_filename(),
        )

    def is_link(self):
        return os.path.islink(self.get_path())

    def get_media_path(self):
        path = os.path.join(
            self.store.yew_dir, self.store.location, self.uid, "media"
        )
        if not os.path.exists(path):
            os.makedirs(path)
            # os.chmod(path, 0x776)
        return path

    def validate(self):
        if not os.path.exists(self.get_path()):
            raise Exception("Non-existant document: %s" % self.path)
        # should also check that we are in sync with index
        return True

    def dump(self):
        click.echo("uid      : %s" % self.uid)
        click.echo("link     : %s" % self.is_link())
        click.echo("title    : %s" % self.name)
        click.echo("location : %s" % self.location)
        click.echo("kind     : %s" % self.kind)
        click.echo("size     : %s" % self.get_size())
        click.echo("digest   : %s" % self.digest)
        click.echo("path     : %s" % self.path)
        click.echo("updated  : %s" % modification_date(self.get_path()))
        click.echo("encrypt  : %s" % self.is_encrypted())


    def get_last_updated_utc(self):
        return modification_date(self.get_path())

    @property
    def updated(self):
        return self.get_last_updated_utc()

    def get_size(self):
        return os.path.getsize(self.get_path())

    def serialize(self, no_uid=False):
        """Serialize as json to send to server."""
        data = {}
        data["uid"] = self.uid
        data["parent"] = None
        data["title"] = self.name
        data["kind"] = self.kind
        data["content"] = self.get_content()  # open(self.get_path()).read()
        data["digest"] = self.digest
        return json.dumps(data)

    def get_content(self):
        """Get the content."""
        f = codecs.open(self.path, "r", "utf-8")
        s = f.read()
        f.close()
        return s

    def put_content(self, content, mode="w"):
        f = codecs.open(self.path, mode, "utf-8")
        f.write(content)
        f.close()

    def __str__(self):
        return self.name



