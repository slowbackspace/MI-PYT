#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from io import StringIO
import os
import textwrap
import pytest
import betamax
import pygithublabeler.run as pygithublabeler

with betamax.Betamax.configure() as config:
    # tell Betamax where to find the cassettes
    # make sure to create the directory
    config.cassette_library_dir = 'tests/fixtures/cassettes'
    if 'AUTH_FILE' in os.environ:
        # If the tests are invoked with an AUTH_FILE environ variable
        TOKEN = pygithublabeler.load_authtoken(os.environ['AUTH_FILE'])
        # Always re-record the cassetes
        # https://betamax.readthedocs.io/en/latest/record_modes.html
        config.default_cassette_options['record_mode'] = 'all'
    else:
        TOKEN = 'false_token'
        # Do not attempt to record sessions with bad fake token
        config.default_cassette_options['record_mode'] = 'none'

    # Hide the token in the cassettes
    config.define_cassette_placeholder('<TOKEN>', TOKEN)


def test_fetch_issues(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    issues = pygithublabeler.fetch_issues(session, 
                                          ("slowbackspace", "testrepo"))
    assert issues[0].get("number", None) is not None


def test_fetch_comments(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    comments = pygithublabeler.fetch_comments(session, 
                                          ("slowbackspace", "testrepo"), 2)
    assert comments[0].get("body", None) is not None


def test_add_labels(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    res = pygithublabeler.add_labels(session, ("slowbackspace", "testrepo"), 
                               16, ["question"])

    assert res[0]["name"] == "question"