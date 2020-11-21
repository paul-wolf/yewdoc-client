import json
from typing import Dict, Optional
import os
import codecs

import click

from .utils import (
    get_sha_digest,
    modification_date,
    slugify,
)

from . import file_system as fs

DOC_KINDS = ["md", "txt", "rst", "json"]


def deserialize(store, data: Dict):
    """Create a document from a dict."""
    return Document(store, data["uid"], data["name"], data["kind"])


class Document(object):
    """Describes a document."""

    def __init__(
        self, store: "YewStore", uid: str, name: str, kind: str, encrypt: int = 0
    ):
        self.store = store
        self.uid = uid
        self.name = name
        self.kind = kind
        self.encrypt = encrypt

    @property
    def path(self):
        return os.path.join(
            self.store.yew_dir,
            self.store.location,
            self.uid,
            f"{self.name}.{self.kind}",
        )

    @property
    def directory_path(self):
        return os.path.join(self.store.yew_dir, self.store.location, self.uid)

    @property
    def digest(self):
        return self.get_digest()

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
        return self.name

    def get_filename(self):
        return "%s.%s" % (self.get_basename(), self.kind)

    def get_path(self):
        return os.path.join(
            self.store.yew_dir,
            self.store.location,
            self.uid,
            self.get_filename(),
        )

    @property
    def path(self):
        return self.get_path()

    def is_link(self):
        return os.path.islink(self.get_path())

    def get_media_path(self):
        path = os.path.join(self.store.yew_dir, self.store.location, self.uid, "media")
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
        click.echo("location : %s" % self.store.location)
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

    def serialize(self, no_uid=False, no_content=False):
        """Serialize as json to send to server."""
        data = {}
        data["uid"] = self.uid
        data["title"] = self.name
        data["kind"] = self.kind
        if not no_content:
            data["content"] = self.get_content()  # open(self.get_path()).read()
        data["digest"] = self.digest
        return data

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

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.name}"
