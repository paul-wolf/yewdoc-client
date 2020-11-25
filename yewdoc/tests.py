# -*- coding: utf-8 -*-
from typing import Final
import os
import json
import shutil
import unittest

import click
import mock
from click.testing import CliRunner

import yewdoc
from yewdoc import file_system as fs
from yewdoc.store import YewStore
from yewdoc.shared import cli


TEST_USERNAME: Final = "_test_user_"
USER_PREFS = {
    "test_user": {
        "location": {
            "default": {
                "url": "https://doc.yew.io",
                "email": "joe.bloggs@blah.com",
                "username": "paul",
                "password": "adsfasdfasdfsadf",
                "first_name": "Joe",
                "last_name": "Bloggs",
                "token": "c099f4d10a163e685289c981eadef04c2b839455",
            }
        }
    }
}


def write_test_user_prefs():
    # this will create the user directory if not exists
    path = os.path.join(fs.get_user_directory(TEST_USERNAME), "settings.json")
    with open(path, "wt") as fp:
        fp.write(json.dumps(USER_PREFS, indent=4))


class MockRemote(object):
    def authenticate_user(self, data):
        return MockResponse(
            {
                "username": "paul",
                "first_name": "Paul",
                "last_name": "Wolf",
                "email": "paul.wolf@blah.com",
                "token": "b9512423d9ffa2312bdcb3d5c60f7db26d5b08a1",
            },
            200,
        )


class MockPreferences:
    def put_user_pref(n, v):
        pass

    def get_user_pref(n):
        return "blah"


class MockStore(object):
    def put_user_pref(self, s, d):
        pass

    @property
    def prefs(self):
        return MockPreferences()


class MockYew(object):
    remote = MockRemote()
    store = MockStore()


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


class TestYewdocsClient(unittest.TestCase):
    def setUp(self):
        self.username = TEST_USERNAME
        test_path = fs.get_user_directory(TEST_USERNAME)
        # we delete entire environment for each test
        # you really would not want to make a mistake here
        if os.path.exists(test_path):
            shutil.rmtree(test_path)

        write_test_user_prefs()
        self.store = YewStore(username=self.username)

    def create_document(self, title, content="my text", kind="md"):
        content = content
        doc = self.store.create_document(title, kind)
        doc.put_content(content)
        return doc

    def test_create_document(self):
        self.create_document("test create document")

    def test_show_document(self):
        self.create_document("test show document")
        runner = CliRunner()
        result = runner.invoke(cli, [f"--user={TEST_USERNAME}", "show", "my test doc"])
        assert result.exit_code == 0

    def test_describe_document(self):

        self.create_document("test describe document")
        runner = CliRunner()
        result = runner.invoke(
            cli, [f"--user={TEST_USERNAME}", "describe", "test describe document"]
        )

        assert result.exit_code == 0
        assert "location" in result.output
        assert "kind" in result.output
        assert "size" in result.output

    def test_info(self):

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                f"--user={TEST_USERNAME}",
                "info",
            ],
        )

        assert result.exit_code == 0
        assert "username" in result.output

    def test_rename_document(self):
        name_old = "test rename document"
        name_new = "renamed document name"
        doc = self.create_document(name_old)
        runner = CliRunner()
        result = runner.invoke(
            cli, [f"--user={TEST_USERNAME}", "rename", name_old, name_new]
        )
        assert result.exit_code == 0
        renamed = self.store.get_doc(doc.uid)
        # assert renamed.name == name_new

    def test_ls_document(self):
        self.create_document("first doc", content="dummy")
        self.create_document("second doc", content="dummy")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                f"--user={TEST_USERNAME}",
                "ls",
            ],
        )
        assert result.exit_code == 0
        assert "first doc" in result.output
        lines = result.output.split("\n")
        assert lines[0] == "first doc"

    def test_tail_document(self):
        self.create_document("test tail document", content="dummy")
        runner = CliRunner()
        result = runner.invoke(
            cli, [f"--user={TEST_USERNAME}", "tail", "test tail document"]
        )
        assert result.exit_code == 0
        assert "dummy" in result.output

    def test_head_document(self):
        self.create_document("test head", content="dummy")
        runner = CliRunner()
        result = runner.invoke(cli, [f"--user={TEST_USERNAME}", "head", "test head"])
        assert result.exit_code == 0
        assert "dummy" in result.output

    @unittest.skip("find out how to keep this from waiting for input")
    def test_kind_document(self):
        self.create_document("test kind doc", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(
            cli, [f"--user={TEST_USERNAME}", "kind", "test kind doc", "txt"]
        )

        assert result.exit_code == 0

    def test_convert_document(self):
        self.create_document("test convert", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(
            cli, [f"--user={TEST_USERNAME}", "convert", "test convert", "html"]
        )

        assert result.exit_code == 0
        assert "<p>dummy</p>" in result.output

    def test_unicode(self):
        name = "my test dóc"
        content = "Ā ā Ă ă Ą ą Ć ć Ĉ ĉ Ċ ċ Č č Ď ď Đ đ Ē ē Ĕ ĕ Ė ė Ę ę Ě ě Ĝ ĝ Ğ ğ Ġ ġ Ģ ģ Ĥ ĥ Ħ ħ Ĩ ĩ Ī ī Ĭ ĭ Į į İ ı Ĳ ĳ Ĵ ĵ Ķ ķ ĸ Ĺ ĺ Ļ ļ Ľ ľ Ŀ ŀ Ł ł Ń ń Ņ ņ Ň ň ŉ Ŋ ŋ Ō ō Ŏ ŏ Ő ő Œ œ Ŕ ŕ Ŗ ŗ Ř ř Ś ś Ŝ ŝ Ş ş Š š Ţ ţ Ť ť Ŧ ŧ Ũ ũ Ū ū Ŭ ŭ Ů ů Ű ű Ų ų Ŵ ŵ Ŷ ŷ Ÿ Ź ź Ż ż Ž ž ſ"
        doc = self.create_document(name, content)
        assert doc.get_content() in content
        content = " ം ഃ അ ആ ഇ ഈ ഉ ഊ ഋ ഌ എ ഏ ഐ ഒ ഓ ഔ ക ഖ ഗ ഘ ങ ച ഛ ജ ഝ ഞ ട ഠ ഡ ഢ ണ ത ഥ ദ ധ ന പ ഫ ബ ഭ മ യ ര റ ല ള ഴ വ ശ ഷ സ ഹ ാ ി ീ ു ൂ ൃ െ േ ൈ ൊ ോ ൌ ് ൗ ൠ ൡ ൦ ൧ ൨ ൩ ൪ ൫ ൬"
        doc = self.create_document(name, content)
        assert doc.get_content() in content

    def test_take(self):
        """Create document via take."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("hello.txt", "w") as f:
                f.write("Hello World!")
            result = runner.invoke(
                cli, [f"--user={TEST_USERNAME}", "take", "hello.txt", "--force"]
            )

            result = runner.invoke(cli, [f"--user={TEST_USERNAME}", "ls", "-l"])
            assert "hello" in result.output
            assert result.exit_code == 0

    def test_ls(self):
        runner = CliRunner()
        result = runner.invoke(cli, [f"--user={TEST_USERNAME}", "ls", "--info"])

        assert result.exit_code == 0
        # assert result.output == 'Hello Peter!\n'

    def test_tag_document(self):
        self.create_document("test tag doc", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                f"--user={TEST_USERNAME}",
                "tag",
                "mytag",
                "test tag doc",
            ],
        )
        assert result.exit_code == 0

    def test_tags(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                f"--user={TEST_USERNAME}",
                "tags",
            ],
        )
        assert result.exit_code == 0

    def test_status(self):
        runner = CliRunner()
        result = runner.invoke(cli, [f"--user={TEST_USERNAME}", "status"])

        assert result.exit_code == 0

    def test_user_pref(self):
        runner = CliRunner()
        runner.invoke(cli, [f"--user={TEST_USERNAME}", "user-pref"])
        #  assert result.exit_code == 0

    @unittest.skip("Not ready for this to work yet")
    def test_authenticate(self):
        yewdoc.yew = MockYew()
        status_code = yewdoc.cmd.authenticate._authenticate("blah", "blah")
        assert status_code == 200


if __name__ == "__main__":
    unittest.main()
