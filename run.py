#!/usr/bin/env python3
import configparser
import time
import json
import re
import yaml

import requests

import click


def get_session(token):
    session = requests.Session()
    session.headers = {'Authorization': 'token ' + token, 'User-Agent': 'testapp'}
    return session

def load_config(file):
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
    rules = yaml.safe_load(open( rules ))
    return rules or []

def get_scope(scope):
    if scope == "all":
        scope = ["issue_body", "issue_comments, pull_requests"]

    return scope

def fetch_issues(session, repo):
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues".format(repo_owner, repo_name))
    r.raise_for_status
    return r.json()

def fetch_comments(session, repo, issue):
    repo_owner, repo_name = repo
    r = session.get("https://api.github.com/repos/{}/{}/issues/{}/comments".format(repo_owner, repo_name, issue))
    r.raise_for_status
    return r.json()

def check_rules(rules, text):
    labels = set()
    for rule in rules:
        #print("Matching pattern {}".format(rule["pattern"]))
        result = re.search(rule["pattern"], text)
        if result != None:
            #print("Match!")
            labels.add(rule["label"])
    return labels

def add_labels(session, repo, issue, labels):
    if len(labels) == 0:
        return False

    # convert labels to list, json.dumps doesn't work with set()
    labels = json.dumps(list(labels))

    print("Adding labels: {} to {}/{} on issue {}".format(labels, repo[0], repo[1], issue))
    repo_owner, repo_name = repo
    r = session.post("https://api.github.com/repos/{}/{}/issues/{}/labels".format(repo_owner, repo_name, issue),
                    data=labels)
    r.raise_for_status
    return r.json()

@click.command()
@click.option('--config', default='auth.cfg', help='Configuration file. Default auth.cfg')
@click.option('--repo', default='slowbackspace/testrepo', help='Repository in \'owner/name\' format. Default slowbackspace/testrepo')
@click.option('--scope', default='issue_body', help='Scope - issue_body, issue_comments, pull_requests, all. Default issue_body.', multiple=True)
@click.option('--rules', default='rules.yml', help='Configuration of rules')
@click.option('--interval', default=5, help='Interval [seconds]. Default 5')
@click.option('--label', default='wontfix', help='Fallback label. Default wonfix.')
def main(config, repo, scope, rules, interval, label):
    cfg = load_config(config)
    token = cfg['github']['token']
    repo_owner, repo_name = get_repo(repo)
    rules = load_rules(rules)
    interval = get_interval(interval)
    fallback_label = get_fallback_label(label)
    scope = get_scope(scope)

    session = get_session(token)

    while True:
        # fetch issues
        issues = fetch_issues(session, (repo_owner, repo_name))

        # loop through every issue, fetch comments if needed, apply rules and add missing labels
        for issue in issues:
            labels = set()
            no_rule_matched = True
            current_labels = [ label["name"] for label in issue["labels"]]

            # skip PR if they aren't in the scope
            if issue.get("pull_request", None) and "pull_requests" not in scope:
                continue

            print ("Inspecting issue #{} '{}' in a repository '{}' ".format(issue["number"], issue["title"], repo_name))

            # aply rules to issues's body if it's in the scope
            if "issue_body" in scope:
                for label in check_rules(rules, issue["body"]):
                    no_rule_matched = False
                    if label not in current_labels:
                        labels.add(label)

            # check comments if needed
            if "issue_comments" in scope:
                comments = fetch_comments(session, (repo_owner, repo_name), issue["number"])
                for comment in comments:
                    for label in check_rules(rules, comment["body"]):
                        no_rule_matched = False
                        if label not in current_labels:
                            labels.add(label)

            # fallback label
            if no_rule_matched:
                if fallback_label not in current_labels:
                    labels.add(fallback_label)

            # add labels to the issue
            res_json = add_labels(session, (repo_owner, repo_name), issue["number"], labels)

        # wait for <interval> seconds
        time.sleep(interval)

if __name__ == '__main__':
    import sys
    sys.exit(int(main() or 0))
