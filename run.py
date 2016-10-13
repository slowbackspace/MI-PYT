#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import json
import os
import re
import time

import requests
from flask import Flask, abort, request

import click
import yaml

app = Flask(__name__)
port = int(os.getenv("PORT", 5000))
debug = True if os.getenv("DEBUG", "") == "true" else False
CONFIG = {}


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
        raise IOError("Could not read config file.")
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


def check_rules(rules, text, current_labels=[]):
    labels = set()
    match = False
    for rule in rules:
        result = re.search(rule["pattern"], text)
        if result is not None:
            match = True
            if rule["label"] not in current_labels:
                labels.add(rule["label"])
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


@app.route('/')
def hello_world():
    return "Hello World! I am running on port {}".format(int(os.getenv("PORT")))


@app.route('/hook', methods=["POST"])
def hook():
    scope = CONFIG["scope"]
    rules = CONFIG["rules"]
    fallback_label = CONFIG["fallback_label"]
    session = CONFIG["session"]

    data = request.get_json()
    if not data:
        abort(501)
    if data.get("action", "") not in ["opened", "created", "edited"]:
        abort(501)
    issue = data.get("issue", None) or data.get("pull_request", None)
    if issue is None:
        return "Invalid requests", 400

    repo_owner, repo_name = get_repo(data.get("repository", {}).get("full_name"))
    comment = data.get("comment", None)
    current_labels = issue.get("labels", [])
    labels = set()
    no_rule_matched = True

    # skip PR if they aren't in the scope
    if data.get("pull_request", None) and "pull_requests" not in scope:
        return "PR not in scope", 400

    # aply rules to issues's body if it's in the scope
    if "issue_body" in scope:
        match, missing_labels = check_rules(rules, issue["body"], current_labels)
        [labels.add(label) for label in missing_labels]
        no_rule_matched = False if match else no_rule_matched

    # check comments if needed
    if "issue_comments" in scope and comment is not None:
        match, missing_labels = check_rules(rules, comment["body"], current_labels)
        [labels.add(label) for label in missing_labels]
        no_rule_matched = False if match else no_rule_matched

    # fallback label
    if no_rule_matched:
        if fallback_label not in current_labels:
            labels.add(fallback_label)

    add_labels(session, (repo_owner, repo_name), issue["number"], labels)
    return "Added labels: {}".format(labels), 200


@click.group()
@click.option('--authconfig', default='auth.cfg', help='Configuration file. Default auth.cfg')
@click.option('--repo', default='slowbackspace/testrepo', help='Repository in \'owner/name\' format. Default slowbackspace/testrepo')
@click.option('--scope', default=["all"], help='Scope - issue_body, issue_comments, pull_requests, all. Default all.', multiple=True)
@click.option('--rules', default='rules.yml', help='Configuration of rules')
@click.option('--interval', default=5, help='Interval [seconds]. Default 5')
@click.option('--label', default='wontfix', help='Fallback label. Default wonfix.')
def cli(authconfig, repo, scope, rules, interval, label):
    auth_cfg = load_authconfig(authconfig)
    token = auth_cfg['github']['token']
    CONFIG.update({
        "token": token,
        "repo_owner": get_repo(repo)[0],
        "repo_name": get_repo(repo)[1],
        "rules": load_rules(rules),
        "interval": get_interval(interval),
        "fallback_label": get_fallback_label(label),
        "scope": get_scope(scope),
        "session": get_session(token)
        })


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
            labels = set()
            no_rule_matched = True
            current_labels = [label["name"] for label in issue["labels"]]

            # skip PR if they aren't in the scope
            if issue.get("pull_request", None) and "pull_requests" not in scope:
                continue

            print("Inspecting issue #{} '{}' in a repository '{}' ".format(
                issue["number"],
                issue["title"], repo_name)
            )

            # aply rules to issues's body if it's in the scope
            if "issue_body" in scope:
                match, missing_labels = check_rules(rules, issue["body"], current_labels)
                [labels.add(label) for label in missing_labels]
                no_rule_matched = False if match else no_rule_matched

            # check comments if needed
            if "issue_comments" in scope:
                comments = fetch_comments(
                    session, (repo_owner, repo_name), issue["number"]
                )
                for comment in comments:
                    match, missing_labels = check_rules(
                        rules, comment["body"], current_labels
                    )
                    [labels.add(label) for label in missing_labels]
                    no_rule_matched = False if match else no_rule_matched

            # fallback label
            if no_rule_matched:
                if fallback_label not in current_labels:
                    labels.add(fallback_label)

            # add labels to the issue
            try:
                add_labels(session, (repo_owner, repo_name), issue["number"], labels)
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
