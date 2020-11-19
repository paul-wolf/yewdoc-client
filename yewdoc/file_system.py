import os
from os.path import expanduser

DEFAULT_USERNAME = "yewser"


def get_gnupg_exists(gnupg_dir=None):
    home = expanduser("~")
    gnupg_dir = gnupg_dir if gnupg_dir else ".gnupg"
    gnupg_home = os.path.join(home, gnupg_dir)
    return os.path.exists(gnupg_home)

def get_username(username=None):
    """Return username.

    Try to get a username that determines the repo of docs.

    Try to get it
       from the caller.
       from the environment
       from a properties file ~/.yew
       user the default constant 'yewser'

    """

    home = expanduser("~")
    file_path = os.path.join(home, ".yew")

    if username:
        return username
    elif os.getenv("YEWDOC_USER"):
        username = os.getenv("YEWDOC_USER")
    elif os.path.exists(file_path):
        config = configparser.ConfigParser()
        with open(file_path, "r") as f:
            s = f.read()
            config.read_string(s)
        try:
            username = config["Yewdoc"]["username"]
        except Exception:
            pass

    return username if username else DEFAULT_USERNAME

def get_user_directory(username=None):
    """Get the directory for the current local user.

    Expand home and then find current yewdocs user.

    If username is not None, use that as user name.

    """
    home = expanduser("~")
    yew_dir = os.path.join(home, ".yew.d", username or get_username())
    if not os.path.exists(yew_dir):
        os.makedirs(yew_dir)
    return yew_dir

def get_storage_directory(username=None):
    """Return path for storage."""
    return get_user_directory(username)

def get_tmp_directory(username=None):
    """Return path for temporary storage."""

    tmp_dir = os.path.join(get_storage_directory(username), "tmp")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir

