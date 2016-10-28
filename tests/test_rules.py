#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from io import StringIO
import os
import pytest
import pygithublabeler.run as pygithublabeler


def test_load_rules(tmpdir):
    content = (
    "- pattern: .*robot:bug.*\n"
    "  label: bug\n"
    "- pattern: .*robot:question.*\n"
    "  label: question\n")

    p = tmpdir.mkdir("sub").join("rules.txt")
    p.write(content)

    rules = pygithublabeler.load_rules(str(p))
    assert len(rules) == 2

    assert rules[0]["label"] == "bug"
    assert rules[0]["pattern"] == ".*robot:bug.*"
    assert rules[1]["label"] == "question"
    assert rules[1]["pattern"] == ".*robot:question.*"


@pytest.mark.parametrize(
    ["rules", "text_list", "current_labels", "fallback_label"],
    [([{"pattern": ".*robot:bug.*", "label": "bug"}], 
        ["Lorem ", "ipsum", "dolor sit amet", "robot:bug"],
        [], "wontfix"),
        ([{"pattern": ".*robot:bug.*", "label": "bug"}], 
         ["Lorem ipsum dolor sit amet,robot:bugconsectetur ,"],
         ["notbug", "question"], "wontfix")]
)
def test_check_rules(rules, text_list, current_labels, fallback_label):
    match, labels = pygithublabeler.check_rules(rules, text_list, current_labels, fallback_label)
    assert match is True and "bug" in labels


def test_check_rules_match_add_nothing():
    rules = [{"pattern": ".*robot:bug.*", "label": "bug"}]
    text_list = ["Lorem ipsum dolor sit amet,robot:bugconsectetur adipiscing elit,"]
    current_labels = ["notbug", "bug"]
    fallback_label = "wontfix"
    match, labels = pygithublabeler.check_rules(rules, text_list, current_labels, fallback_label)
    assert match is True and len(labels) == 0


def test_check_rules_no_match():
    rules = [{"pattern": ".*robot:bug.*", "label": "bug"}]
    text_list = ["Lorem ipsum dolor sit amet, consectetur adipiscing elit,"]
    current_labels = []
    fallback_label = "wontfix"
    match, labels = pygithublabeler.check_rules(rules, text_list,
                                                current_labels, fallback_label)
    assert match is False and fallback_label in labels


def test_check_rules_no_match_add_nothing():
    rules = [{"pattern": ".*robot:bug.*", "label": "bug"}]
    text_list = ["Lorem ipsum dolor sit amet, consectetur adipiscing elit,"]
    current_labels = ["wontfix"]
    fallback_label = "wontfix"
    match, labels = pygithublabeler.check_rules(rules, text_list,
                                                current_labels, fallback_label)
    assert match is False and len(labels) == 0


def test_check_rules_without_rules_text():
    rules = []
    text_list = []
    current_labels = []
    fallback_label = "wontfix"
    match, labels = pygithublabeler.check_rules(rules, text_list, current_labels, fallback_label)
    assert match is False and fallback_label in labels
