import os
import json
from typing import Dict, Optional

import glom

from . import file_system as fs


"""
put user prefs in json in user dir:

yew.d/<username>/settings.json

"""
global_preferences = ["username", "offline"]


USER_PREFERENCES = [
    "location.default.url",
    "location.default.email",
    "location.default.username",
    "location.default.password",
    "location.default.first_name",
    "location.default.last_name",
    "location.default.token",
]


def read_user_prefs(username) -> Dict:
    """Read the settings file as json into data.
    The settings.json is in the user directory:
    ~/.yew.d/<username>/
    """
    path = os.path.join(fs.get_user_directory(username), "settings.json")
    if not os.path.exists(path):
        raise Exception(f"Settings file not found at: {path}")
    with open(path) as f:
        data = json.load(f)
    return data


def write_user_prefs(username, data) -> None:
    """Write the prefs file as json in the root dir."""
    path = os.path.join(fs.get_user_directory(username), "settings.json")
    with open(path, "wt") as f:
        f.write(json.dumps(data, indent=4))


class Preferences:
    def __init__(self, username: Optional[str] = None):
        self.username = username
        self.data = read_user_prefs(self.username)

    def get_user_pref(self, k):
        try:
            return glom.glom(self.data, k)
        except glom.core.PathAccessError:
            return None

    def put_user_pref(self, k, v):
        new_data = glom.assign(self.data, k, v, missing=dict)
        write_user_prefs(self.username, new_data)

    def delete_user_pref(self, k):
        new_data = glom.delete(self.data, k, ignore_missing=True)
        write_user_prefs(self.username, new_data)

    def update_recent(self, doc):
        """Update most recent list.

        Return list of uids.

        """

        list_unparsed = self.get_user_pref("recent_list")
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
        else:
            list_parsed = []
        if doc.uid in list_parsed:
            list_parsed.remove(doc.uid)  # take it out
        list_parsed.insert(0, doc.uid)  # make it the first one
        # now save the new list
        self.put_user_pref("recent_list", json.dumps(list_parsed))

    def get_recent(self):
        """Get most recent documents."""

        list_unparsed = self.get_user_pref("recent_list")
        docs = []
        if list_unparsed:
            list_parsed = json.loads(list_unparsed)
            for uid in list_parsed:
                d = self.get_doc(uid)
                if d:
                    docs.append(d)
            return docs
        return []
