#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from io import StringIO
import os
import json
import pytest
import betamax
import pygithublabeler.run as pygithublabeler

TEST_REPOSITORY = ("slowbackspace", "testrepo")
TEST_ISSUE = 16

with betamax.Betamax.configure() as config:
    # tell Betamax where to find the cassettes
    # make sure to create the directory
    config.cassette_library_dir = 'tests/fixtures/cassettes'
    if 'AUTH_FILE' in os.environ:
        # If the tests are invoked with an AUTH_FILE environ variable
        TOKEN = pygithublabeler.load_authtoken(os.environ['AUTH_FILE'])
        # https://betamax.readthedocs.io/en/latest/record_modes.html
        config.default_cassette_options['record_mode'] = 'once'
    else:
        TOKEN = 'false_token'
        # Do not attempt to record sessions with bad fake token
        config.default_cassette_options['record_mode'] = 'none'

    # Hide the token in the cassettes
    config.define_cassette_placeholder('<TOKEN>', TOKEN)


@pytest.fixture
def testapp():
    pygithublabeler.app.config['TESTING'] = True
    return pygithublabeler.app.test_client()


@pytest.fixture
def testapp_with_session(betamax_session):
    pygithublabeler.app.config['TESTING'] = True
    pygithublabeler.app.config['session'] = betamax_session
    return pygithublabeler.app.test_client()


def test_fetch_issues(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    issues = pygithublabeler.fetch_issues(session, 
                                          TEST_REPOSITORY)
    assert issues[0].get("number", None) is not None


def test_fetch_comments(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    comments = pygithublabeler.fetch_comments(session, 
                                          TEST_REPOSITORY, 2)
    assert comments[0].get("body", None) is not None


def test_add_labels(betamax_session):
    session = pygithublabeler.get_session(TOKEN, betamax_session)
    labels = pygithublabeler.add_labels(session, TEST_REPOSITORY, 
                               TEST_ISSUE, ["question"])

    assert "question" in [label["name"] for label in labels]


def test_index(testapp):
    assert 'pygithub-labeler' in testapp.get('/').data.decode('utf-8')


def test_hook_get(testapp):
    assert 'pygithub-labeler' in testapp.get('/hook').data.decode('utf-8')


def test_hook_post(testapp, testapp_with_session, betamax_session):
    # without data
    r = testapp.post('/hook')
    res_content = r.data.decode('utf-8')
    assert r.status_code == 400 and "Invalid data" in res_content

    # invalid action
    data = {"action": "invalid_action"}
    r = testapp.post('/hook', data=json.dumps(data), content_type="application/json")
    res_content = r.data.decode('utf-8')
    assert r.status_code == 501 and "Invalid action" in res_content

    # without issue
    data = {"action": "opened"}
    r = testapp.post('/hook', data=json.dumps(data), content_type="application/json")
    res_content = r.data.decode('utf-8')
    assert r.status_code == 400 and "Invalid requests" in res_content

    # fake issue
    repository_fullname = "{}/{}".format(TEST_REPOSITORY[0], TEST_REPOSITORY[1])
    data = {
        "action": "opened", 
        "issue": {
            "number": TEST_ISSUE,
            "labels": [],
            "body": "testovaci robot:bug text"
        },
        "repository": {"full_name": repository_fullname}
        }
    r = testapp_with_session.post('/hook', data=json.dumps(data), content_type="application/json")
    res_content = r.data.decode('utf-8')
    assert r.status_code == 200 and "bug" in res_content
