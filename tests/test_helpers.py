#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from io import StringIO
import os
import pytest
import pygithublabeler.run as pygithublabeler


def test_validate_signature():
    result = pygithublabeler.validate_signature(
        headers={"X-Hub-Signature": "sha1=433b5f0083eb9f61fa3c5977f8564bb7e72d4971"},
        data="testmsg".encode("utf-8"),
        secret_key="secret_key")
    assert result is True


def test_validate_signature_invalid_signature():
    result = pygithublabeler.validate_signature(
        headers={"X-Hub-Signature": "sha1=433b5f0083eb9fINVALIDf8564bb7e72d4971"},
        data="testmsg".encode("utf-8"),
        secret_key="secret_key")
    assert result is False


def test_get_session_headers():
    session = pygithublabeler.get_session("secret")
    assert session.headers["Authorization"] == "token secret"


def test_get_repo():
    repo_owner, repo_name = pygithublabeler.get_repo("owner/name")
    assert (repo_owner, repo_name) == ("owner", "name")


def test_get_repo_fail():
    with pytest.raises(ValueError):
        repo_owner, repo_name = pygithublabeler.get_repo("ownername")


def test_load_authconfig(tmpdir):
    content = """[github]
            token = TOKEN_THAT_IS_100_PER_LEGIT
            """
    p = tmpdir.mkdir("sub").join("auth.txt")
    p.write(content)

    token = pygithublabeler.load_authtoken(str(p))
    assert token == "TOKEN_THAT_IS_100_PER_LEGIT"


def test_load_authconfig_fail():
    filename = "file_that_most_likely_does_not_exits.omg"
    with pytest.raises(IOError):
        pygithublabeler.load_authtoken(filename)
