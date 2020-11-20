import codecs
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import traceback
import uuid
import tarfile

import dateutil
import dateutil.parser
import humanize as h
import markdown
import pytz
import tzlocal


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

def tar_directory(path, tar_filename, mode="w:gz"):
    """Tar with compression a directory and its subdirectories."""
    
    with tarfile.open(tar_filename, mode) as tar_handle:
        for root, dirs, files in os.walk(path):
            for file in files:
                tar_handle.add(os.path.join(root, file))
                
def is_binary_string():
    textchars = bytearray([7, 8, 9, 10, 12, 13, 27]) + bytearray(range(0x20, 0x100))
    return bool(bytes.translate(None, textchars))


def is_binary_file(fullpath):
    return is_binary_string(open(fullpath, "rb").read(1024))


def slugify(value):
    """Stolen from Django: convert name.
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata

    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    # ... re.sub(r'[-\s]+', '-', value)
    value = "-".join(value.split()).lower()
    return value


def err():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(
        exc_type, exc_value, exc_traceback, limit=5, file=sys.stdout
    )


def is_uuid(uid):
    """Return non-None if uid is a uuid."""
    uuidregex = re.compile(
        r"[0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12}\Z", re.I
    )
    return uuidregex.match(uid)


def is_short_uuid(s):
    """Return non-None if uid is a uuid."""
    uuid_short_regex = re.compile(r"[0-9a-f]{8}\Z", re.I)
    return uuid_short_regex.match(s)


def get_short_uid(s):
    return s.split("-")[0]


def delete_directory(folder):
    """Delete directory p and all sub directories and files."""
    try:
        shutil.rmtree(folder)
    except Exception as e:
        print(e)


def get_sha_digest(s):
    """Generate digest for s.

    Trim final whitespace.
    Convert to byte string.
    Produce digest.

    """
    s = s.rstrip()
    s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def to_utc(dt):
    """Convert datetime object to utc."""
    local_tz = tzlocal.get_localzone().localize(dt)
    return local_tz.astimezone(pytz.utc)


def modification_date(path):
    """Get modification date of path as UTC time."""
    t = os.path.getmtime(path)
    return to_utc(datetime.datetime.fromtimestamp(t))
