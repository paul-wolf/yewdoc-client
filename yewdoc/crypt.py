# -*- coding: utf-8 -*-
import os
import sys
import gnupg
from pprint import pprint
import argparse
import importlib
import getpass
from collections import namedtuple


def gpgh(gpg_dir):
    default_gpg_dir = gpg_dir if gpg_dir else ".gnupg"
    home = os.path.expanduser("~")
    return f"{home}/{default_gpg_dir}"


def get_gpg(args):
    return gnupg.GPG(gnupghome=gpgh(args.gpg_dir))


def _get_input():
    print("Enter/Paste your content. Ctrl-D or Ctrl-Z ( windows ) to save it.")
    contents = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        contents.append(line)
    return contents


def _get_passphrase():
    return getpass.getpass("Enter passphrase: ")


def create_key(args):
    gpg = get_gpg(args)
    passphrase = _get_passphrase()
    input_data = gpg.gen_key_input(name_email=args.email, passphrase=passphrase)
    key = gpg.gen_key(input_data)
    print(key)


def export_keys(args):
    gpg = get_gpg(args)
    ascii_armored_public_keys = gpg.export_keys(args.key)
    ascii_armored_private_keys = gpg.export_keys(
        args.key, True, passphrase=args.passphrase
    )
    print(ascii_armored_public_keys)
    print(ascii_armored_private_keys)


def import_keys(args):
    gpg = get_gpg(args)
    key_data = open(args.file).read()
    import_result = gpg.import_keys(key_data)
    pprint(import_result.results)


def list_keys(args):
    gpg = get_gpg(args)
    public_keys = gpg.list_keys()
    private_keys = gpg.list_keys(True)
    # print('public keys:')
    # pprint(public_keys)
    #  print('private keys:')
    #  pprint(private_keys)
    return (public_keys, private_keys)


def encrypt_input(args):
    gpg = get_gpg(args)
    s = "\n".join(_get_input())
    encrypted_data = gpg.encrypt(s, args.email)
    encrypted_string = str(encrypted_data)
    #  print('ok: ', encrypted_data.ok)
    #  print('status: ', encrypted_data.status)
    #  print('stderr: ', encrypted_data.stderr)
    #  print('unencrypted_string: ', unencrypted_string)
    #  print('encrypted_string: ', encrypted_string)
    print(encrypted_string)


def encrypt_file(path, email, gpghome):
    Args = namedtuple("Args", "gpg_dir")
    args = Args(gpg_dir=gpghome)
    gpg = get_gpg(args)
    with open(path, "rb") as f:
        status = gpg.encrypt_file(f, recipients=[email], output=path)
    return status


def decrypt_file(path, email, gpghome):
    Args = namedtuple("Args", "gpg_dir")
    args = Args(gpg_dir=gpghome)
    gpg = get_gpg(args)
    passphrase = _get_passphrase()
    print("Passphrase: [{}]".format(passphrase))
    with open(path, "rb") as f:
        status = gpg.decrypt_file(f, passphrase=passphrase, output=path)
    print("ok: ", status.ok)
    print("status: ", status.status)
    print("stderr: ", status.stderr)


def main(args):
    m = importlib.import_module(__name__)
    getattr(m, args.operation)(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Key man")
    parser.add_argument(
        "operation", type=str, default="list", help="operation to perform"
    )
    parser.add_argument("--email", type=str, help="email of key identity", default=None)
    parser.add_argument("--key", type=str, help="key fingerprint or id", default=None)
    parser.add_argument("--passphrase", type=str, help="passphrase", default=None)
    parser.add_argument("--file", type=str, help="path to a file", default=None)
    parser.add_argument(
        "--gpg_dir", type=str, help="GNUGPG directory; default=.gnupg", default=None
    )
    args = parser.parse_args()
    main(args)
