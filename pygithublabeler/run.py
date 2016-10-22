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
CONFIG = {"webhook_token": os.getenv("webhook_token", "")}
ROOT_DIRECTORY = os.path.realpath(__file__)
app = Flask(__name__)


def validate_signature(headers, data, secret_key):
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


def get_session(token):
    session = requests.Session()
    session.headers = {
        "Authorization": "token " + token,
        "User-Agent": "testapp"
    }
    return session


def load_authconfig(file):
    config = configparser.ConfigParser()
    if len(config.read(file)) == 0:
        raise IOError("Could not read config file {}.".format(file))
    return config


def get_repo(repo):
    repo_owner, repo_name = repo.split("/")
    return repo_owner, repo_name


def get_interval(interval):
    return interval


def get_fallback_label(label):
    return label


def load_rules(rules):
    with open(rules) as f:
        rules = yaml.safe_load(f)
        return rules or []


def get_scope(scope):
    if "all" in scope:
        scope = ["issue_body", "issue_comments", "pull_requests"]

    return scope


def fetch_issues(session, repo):
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues".format(
        repo_owner, repo_name)
    )
    r.raise_for_status
    return r.json()


def fetch_comments(session, repo, issue):
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues/{}/comments".format(
        repo_owner, repo_name, issue)
    )
    r.raise_for_status
    return r.json()


def check_rules(rules, text_list, current_labels, fallback_label):
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
    if len(labels) == 0:
        return False

    # convert labels to list, json.dumps doesn't work with set()
    labels = json.dumps(list(labels))

    print("Adding labels: {} to {}/{} on issue {}".format(labels, repo[0], repo[1], issue))
    repo_owner, repo_name = repo
    r = session.post("https://api.github.com/repos/{}/{}/issues/{}/labels".format(
        repo_owner, repo_name, issue),
        data=labels
    )
    r.raise_for_status
    return r.json()


def load_configuration(authconfig="auth.cfg", repo="slowbackspace/testrepo",
                        scope=["all"], rules="rules.yml", interval=10,
                        fallback_label="wontfix"):
    try:
        auth_cfg = load_authconfig(authconfig)
        token = auth_cfg['github']['token']
    except Exception as e:
        sys.exit("Unable to read auth configuration from '{}'".format(authconfig))
    
    try:
        rules = load_rules(rules)
    except Exception as e:
        sys.exit("Unable to read rules configuration from '{}'".format(rules))

    CONFIG.update({
        "token": token,
        "repo_owner": get_repo(repo)[0],
        "repo_name": get_repo(repo)[1],
        "rules": rules,
        "interval": get_interval(interval),
        "fallback_label": get_fallback_label(fallback_label),
        "scope": get_scope(scope),
        "session": get_session(token)
        })


@app.route('/')
def index():
    return render_template("help.html")
    # return "Hello World! I am running on port {}".format(int(os.getenv("PORT")))


@app.route('/hook', methods=["POST", "GET"])
def hook():
    if not CONFIG.get("scope", None):
        load_configuration()
    scope = CONFIG["scope"]
    rules = CONFIG["rules"]
    fallback_label = CONFIG["fallback_label"]
    session = CONFIG["session"]

    if request.method == "GET":
        return render_template("help.html")

    try:
        data = request.get_json()
    except Exception as e:
        return abort(400)

    if not data:
        abort(501)
    if data.get("action", "") not in ["opened", "created", "edited"]:
        abort(501)
    issue = data.get("issue", None) or data.get("pull_request", None)
    if issue is None:
        return "Invalid requests", 400

    # Validate request
    if not debug:
        if CONFIG["webhook_token"] == "":
            print("Missing webhook_token env variable. Webhook endpoint not secured.")
        elif not validate_signature(request.headers, request.data, CONFIG["webhook_token"]):
            abort(403)

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

    add_labels(session, (repo_owner, repo_name), issue["number"], missing_labels)
    return "Added labels: {}".format(missing_labels), 200


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
    """Run the cli app"""
    session = CONFIG["session"]
    scope = CONFIG["scope"]
    rules = CONFIG["rules"]
    fallback_label = CONFIG["fallback_label"]
    interval = CONFIG["interval"]
    repo_owner, repo_name = CONFIG["repo_owner"], CONFIG["repo_name"]

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
