#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from goloka.core import KeyRing


def test_keyring_user_proejct_stat_key():
    ("KeyRing.for_user_project_stats_list should return a key for where the request list is stored")

    # Given I call
    key = KeyRing.for_user_project_stats_list("gabrielfalcao", "sure")

    # Then it should be the expected key
    key.should.equal("list:stats:github:gabrielfalcao/sure")


def test_keyring_user_stat_key():
    ("KeyRing.for_user_project_name_set should return a key for where the request list is stored")

    # Given I call
    key = KeyRing.for_user_project_name_set("gabrielfalcao")

    # Then it should be the expected key
    key.should.equal("set:github:gabrielfalcao")
