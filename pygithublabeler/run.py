#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import hashlib
import hmac
import json
import os
import re
import time
import sys

import requests
from flask import Flask, abort, request, redirect, render_template

import click
import yaml

port = int(os.getenv("PORT", 5000))
debug = True if os.getenv("DEBUG", "") == "true" else False
ROOT_DIRECTORY = os.path.realpath(__file__)
app = Flask(__name__)
app.config.update({"webhook_token": os.getenv("webhook_token", "")})


def validate_signature(headers, data, secret_key):
    """Validate webhook request with a signature in X-Hub-Signature header
    
    More info at https://developer.github.com/webhooks/securing/ 
    
    Args:
        headers (dict): Request's headers
        data (str): Request's data
        secret_key (str): Top secret webhook token
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    # http://eli.thegreenplace.net/2014/07/09/payload-server-in-python-3-for-github-webhooks
    # https://github.com/jirutka/github-pr-closer/blob/master/app.py
    try:
        sha_name, signature = headers["X-Hub-Signature"].split("=", 1)
    except Exception as e:
        return False

    if sha_name != "sha1":
        return False

    computed_digest = hmac.new(secret_key.encode("utf-8"),
                               msg=data,
                               digestmod=hashlib.sha1).hexdigest()

    return hmac.compare_digest(computed_digest, signature)


def get_session(token, custom_session=None):
    """Get requests session with authorization headers
    
    Args:
        token (str): Top secret GitHub access token
        custom_session: e.g. betamax's session
    
    Returns:
        :class:`requests.sessions.Session`: Session 
    """
    session = custom_session or requests.Session()
    session.headers = {
        "Authorization": "token " + token,
        "User-Agent": "testapp"
    }
    return session


def load_authtoken(filename):
    """Reads authorization token from a file.
    
    Args:
        filename (str): path to the file
    
    Returns:
        str: Top secret webhook token 
    """
    config = configparser.ConfigParser()
    if len(config.read(filename)) == 0:
        raise IOError("Could not read config file {}.".format(filename))

    token = config['github']['token']
    return token


def load_rules(filename):
    """Reads rules for labelling from a YAML file.
    
    Args:
        filename (str): path to the file
    
    Returns:
        list: list of rules or empty list if file failed to load 
    """
    with open(filename) as f:
        rules = yaml.safe_load(f)
        return rules or []


def get_repo(repo):
    """Parse owner and name of the repository from repository's fullname
    
    Args:
        repo (str): Full name of the repository (owner/name format)
    
    Returns:
        tuple: (owner, name)
    """
    repo_owner, repo_name = repo.split("/")
    return repo_owner, repo_name


def get_scope(scope):
    """Get scope for the labeler
    
    Args:
        scope (list): combination of issue_body, issue_comments, pull_requests or ["all"]
    
    Returns:
        list: list of scopes
    """
    if "all" in scope:
        scope = ["issue_body", "issue_comments", "pull_requests"]

    return scope


def fetch_issues(session, repo):
    """Fetch list of issues for the repository
    
    Args:
        session (Session): Request's session
        repo (tuple): (repository_owner, repository_name) 
    Returns:
        dict: JSON Response
    """
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues".format(
        repo_owner, repo_name)
    )
    r.raise_for_status
    return r.json()


def fetch_comments(session, repo, issue):
    """Fetch issue's comments
    
    Args:
        session (Session): Request's session
        repo (tuple): (repository_owner, repository_name) 
        issue (int): Issue's number
    Returns:
        dict: JSON Response
    """
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues/{}/comments".format(
        repo_owner, repo_name, issue)
    )
    r.raise_for_status
    return r.json()


def check_rules(rules, text_list, current_labels, fallback_label):
    """Finds rule's match in a text and returns list of labels to attach.
    If no rule matches returns False for match and fallback label will be attached.
    
    Args:
        rules (list): List of rules
        text_list (list): List of strings to search in
        current_labels (list): List of already attached labels
        fallback_label (str): Label to attach if no rule matches
    Returns:
        tuple: (match, labels)

            match (bool): True if any rule matches, False otherwise
            labels (list): List of labels to attach
    """
    labels = set()
    match = False
    for rule in rules:
        for text in text_list:
            result = re.search(rule["pattern"], text)
            if result is not None:
                match = True
                if rule["label"] not in current_labels:
                    labels.add(rule["label"])
    # fallback label
    if not match:
        if fallback_label not in current_labels:
            labels.add(fallback_label)
    return match, labels


def add_labels(session, repo, issue, labels):
    """Sends request to Github API to attach the labels to the issue

    Args:
        session (Session): Request's session
        repo (tuple): (repository_owner, repository_name) 
        issue (int): Issue's number
        labels (list): List of labels to attach
    Returns:
        dict: JSON Response
    """
    if len(labels) == 0:
        return False

    # convert labels to list, json.dumps doesn't work with set()
    labels = json.dumps(list(labels))

    print("Adding labels: {} to {}/{} on issue {}".format(labels, repo[0], repo[1], issue))
    repo_owner, repo_name = repo
    url = "https://api.github.com/repos/{}/{}/issues/{}/labels".format(
                                                repo_owner, repo_name, issue)
    r = session.post(url, data=labels)
    r.raise_for_status
    return r.json()


def load_configuration(authconfig="auth.cfg", repo="slowbackspace/testrepo",
                        scope=["all"], rules="rules.yml", interval=10,
                        fallback_label="wontfix"):
    """Loads configuration and store it in app.config
    
    Args:
        authconfig (str): Path to the authorization config
        repo (tuple): (repository_owner, repository_name) 
        scope (list): list of scopes
        rules (str): Path to the rules config
        interval (int): How often scan issues
        fallback_label (str): Label that will be attached if no rule matches
    """
    try:
        token = load_authtoken(authconfig)
    except Exception as e:
        sys.exit("Unable to read auth configuration from '{}'".format(authconfig))
    
    try:
        rules = load_rules(rules)
    except Exception as e:
        sys.exit("Unable to read rules configuration from '{}'".format(rules))

    app.config.update({
        "token": token,
        "repo_owner": get_repo(repo)[0],
        "repo_name": get_repo(repo)[1],
        "rules": rules,
        "interval": interval,
        "fallback_label": fallback_label,
        "scope": get_scope(scope),
        "session": app.config.get("session", None) or get_session(token)
        })


@app.route('/')
def index():
    """ Index page """
    return render_template("help.html")
    # return "Hello World! I am running on port {}".format(int(os.getenv("PORT")))


@app.route('/hook', methods=["POST", "GET"])
def hook():
    """Handler for the GitHub webhook
    Supports 3 types of GitHub events - issues, issue comment, pull request.
    Validates requests and verifies signature using :py:func:`validate_signature`.
    Then text of the issue/comment 
    Then it will find and add missing labels to the issue. 
    """
    if request.method == "GET":
        return render_template("help.html")

    if not app.config.get("scope", None):
        load_configuration()
    scope = app.config["scope"]
    rules = app.config["rules"]
    fallback_label = app.config["fallback_label"]
    session = app.config["session"]

    try:
        data = request.get_json()
    except Exception as e:
        return abort(400)

    if not data:
        return "Invalid data", 400
    if data.get("action", "") not in ["opened", "created", "edited"]:
        return "Invalid action", 501
    issue = data.get("issue", None) or data.get("pull_request", None)
    if issue is None:
        return "Invalid requests", 400

    # Validate request
    if not debug:
        if app.config["webhook_token"] == "":
            print("Missing webhook_token env variable. Webhook endpoint not secured.")
        elif not validate_signature(request.headers, request.data, app.config["webhook_token"]):
            return "Invalid signature", 403

    repo_owner, repo_name = get_repo(data.get("repository", {}).get("full_name"))
    comment = data.get("comment", None)
    current_labels = [label["name"] for label in issue.get("labels", [])]
    searched_content = []
    # skip PR if they aren't in the scope
    if data.get("pull_request", None) and "pull_requests" not in scope:
        return "PR not in scope", 400

    # aply rules to issues's body if it's in the scope
    if "issue_body" in scope:
        searched_content.append(issue["body"])

    # check comments if needed
    if "issue_comments" in scope and comment is not None:
        searched_content.append(comment["body"])

    match, missing_labels = check_rules(rules, searched_content,
                                        current_labels, fallback_label)

    res = add_labels(session, (repo_owner, repo_name), issue["number"], missing_labels)
    return "{}".format(missing_labels), 200


@click.group()
@click.option('--authconfig', default='auth.cfg', help='Configuration file. Default auth.cfg')
@click.option('--repo', default='slowbackspace/testrepo', help='Repository in \'owner/name\' format. Default slowbackspace/testrepo')
@click.option('--scope', default=["all"], help='Scope - issue_body, issue_comments, pull_requests, all. Default all.', multiple=True)
@click.option('--rules', default='rules.yml', help='Configuration of rules')
@click.option('--interval', default=5, help='Interval [seconds]. Default 5')
@click.option('--label', default='wontfix', help='Fallback label. Default wonfix.')
def cli(authconfig, repo, scope, rules, interval, label):
    load_configuration(authconfig, repo, scope, rules, interval, label)


@cli.command()
def console():
    """Run the cli app
    Periodically fetches issues from the GitHub API and attaches missing labels.
    """
    session = app.config["session"]
    scope = app.config["scope"]
    rules = app.config["rules"]
    fallback_label = app.config["fallback_label"]
    interval = app.config["interval"]
    repo_owner, repo_name = app.config["repo_owner"], app.config["repo_name"]

    while True:
        # fetch issues
        issues = fetch_issues(session, (repo_owner, repo_name))

        # loop through every issue
        # fetch comments if needed
        # apply rules and add missing labels
        for issue in issues:
            searched_content = []
            # skip PR if they aren't in the scope
            if issue.get("pull_request", None) and "pull_requests" not in scope:
                continue

            print("Inspecting issue #{} '{}' in a repository '{}' ".format(
                issue["number"],
                issue["title"], repo_name)
            )

            current_labels = [label["name"] for label in issue["labels"]]

            # aply rules to issues's body if it's in the scope
            if "issue_body" in scope:
                searched_content.append(issue["body"])

            # check comments if needed
            if "issue_comments" in scope:
                comments = fetch_comments(
                    session, (repo_owner, repo_name), issue["number"]
                )
                [searched_content.append(comment["body"]) for comment in comments]

            match, missing_labels = check_rules(rules, searched_content,
                                                current_labels, fallback_label)
            # add labels to the issue
            try:
                add_labels(
                    session,
                    (repo_owner, repo_name),
                    issue["number"],
                    missing_labels
                )
            except Exception as e:
                print(e)

        # wait for <interval> seconds
        time.sleep(interval)


@cli.command()
def web():
    """Run the web app"""
    app.run(host="0.0.0.0", debug=debug, port=port)


if __name__ == '__main__':
    import sys
    sys.exit(int(cli() or 0))
