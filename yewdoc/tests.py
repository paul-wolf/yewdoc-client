# -*- coding: utf-8 -*-
import os
import shutil
import unittest
import mock
import click
from click.testing import CliRunner

from yewdoc import (
    YewStore,
    cli,
    api,
    attach,
    browse,
    configure,
    context,
    convert,
    create,
    delete,
    describe,
    diff,
    edit,
    find,
    global_pref,
    head,
    ls,
    ping,
    push,
    read,
    register,
    rename,
    show,
    status,
    sync,
    tag,
    tail,
    take,
    user_pref,
)

import yewdoc


class MockRemote(object):
    def authenticate_user(self, data):
        return MockResponse(
            {
                u"username": "paul",
                u"first_name": u"Paul",
                u"last_name": u"Wolf",
                u"email": u"paul.wolf@blah.com",
                u"token": u"b9512423d9ffa2312bdcb3d5c60f7db26d5b08a1",
            },
            200,
        )


class MockStore(object):
    def put_user_pref(self, s, d):
        pass


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
        self.username = "test_user"
        test_path = "{}/.yew.d/{}".format(os.path.expanduser("~"), self.username)

        # we delete entire environment for each test
        if os.path.exists(test_path):
            shutil.rmtree(test_path)

        self.store = YewStore(username=self.username)

    def create_document(self, title, content="my text", kind="md"):
        content = content
        doc = self.store.create_document(title, "default", kind)
        # doc.put_content(content.decode('utf-8'))
        doc.put_content(content)
        return doc

    def test_create_document(self):
        self.create_document("my test doc")

    def test_show_document(self):
        self.create_document("my test doc")
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "show", "my test doc"])
        assert result.exit_code == 0

    def test_describe_document(self):
        self.create_document("my test doc")
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "describe", "my test doc"])
        assert result.exit_code == 0
        assert u"location" in result.output
        assert u"kind" in result.output
        assert u"size" in result.output

    def test_tail_document(self):
        self.create_document("my test doc", content="dummy")
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "tail", "my test doc"])
        assert result.exit_code == 0
        assert "dummy" in result.output

    def test_head_document(self):
        self.create_document("my test doc", content="dummy")
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "head", "my test doc"])
        assert result.exit_code == 0
        assert "dummy" in result.output

    def test_kind_document(self):
        self.create_document("my test doc", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "kind", "my test doc", "txt"])
        print(result.output)
        #  assert result.exit_code == 0

    def test_rename_document(self):
        self.create_document("my test doc", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--user=test_user", "rename", "my test doc", "my new test doc"]
        )
        print(result.output)
        # assert result.exit_code == 0

    def test_convert_document(self):
        self.create_document("my test doc", content="dummy", kind="md")
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--user=test_user", "convert", "my test doc", "html"]
        )
        print(result.output)
        assert result.exit_code == 0
        assert "<p>dummy</p>" in result.output

    def test_unicode(self):
        name = u"my test dóc"
        content = u"Ā ā Ă ă Ą ą Ć ć Ĉ ĉ Ċ ċ Č č Ď ď Đ đ Ē ē Ĕ ĕ Ė ė Ę ę Ě ě Ĝ ĝ Ğ ğ Ġ ġ Ģ ģ Ĥ ĥ Ħ ħ Ĩ ĩ Ī ī Ĭ ĭ Į į İ ı Ĳ ĳ Ĵ ĵ Ķ ķ ĸ Ĺ ĺ Ļ ļ Ľ ľ Ŀ ŀ Ł ł Ń ń Ņ ņ Ň ň ŉ Ŋ ŋ Ō ō Ŏ ŏ Ő ő Œ œ Ŕ ŕ Ŗ ŗ Ř ř Ś ś Ŝ ŝ Ş ş Š š Ţ ţ Ť ť Ŧ ŧ Ũ ũ Ū ū Ŭ ŭ Ů ů Ű ű Ų ų Ŵ ŵ Ŷ ŷ Ÿ Ź ź Ż ż Ž ž ſ"
        doc = self.create_document(name, content)
        assert doc.get_content() in content
        content = u" ം ഃ അ ആ ഇ ഈ ഉ ഊ ഋ ഌ എ ഏ ഐ ഒ ഓ ഔ ക ഖ ഗ ഘ ങ ച ഛ ജ ഝ ഞ ട ഠ ഡ ഢ ണ ത ഥ ദ ധ ന പ ഫ ബ ഭ മ യ ര റ ല ള ഴ വ ശ ഷ സ ഹ ാ ി ീ ു ൂ ൃ െ േ ൈ ൊ ോ ൌ ് ൗ ൠ ൡ ൦ ൧ ൨ ൩ ൪ ൫ ൬"
        doc = self.create_document(name, content)
        assert doc.get_content() in content

    def test_take(self):
        """Create document via take."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("hello.txt", "w") as f:
                f.write("Hello World!")
            result = runner.invoke(
                cli, ["--user=test_user", "take", "hello.txt", "--force"]
            )
            print(result.output)
            result = runner.invoke(cli, ["--user=test_user", "ls", "-l"])
            assert "hello" in result.output
            assert result.exit_code == 0

    def test_ls(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "ls", "--info"])
        print(result.output)
        assert result.exit_code == 0
        # assert result.output == 'Hello Peter!\n'

    def test_status(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--user=test_user", "status"])
        print(result.output)
        assert result.exit_code == 0

    def test_global_pref(self):
        runner = CliRunner()
        runner.invoke(cli, ["global-pref"])
        # assert result.exit_code == 0
        # print(result.output)

    def test_user_pref(self):
        runner = CliRunner()
        runner.invoke(cli, ["--user=test_user", "user-pref"])
        #  assert result.exit_code == 0
        # print(result.output)

    def test_authenticate(self):
        yewdoc.yew = MockYew()
        status_code = yewdoc._authenticate("blah", "blah")
        assert status_code == 200


if __name__ == "__main__":
    unittest.main()
