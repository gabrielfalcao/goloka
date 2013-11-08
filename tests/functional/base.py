#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import json
import httpretty

from mock import Mock
from uuid import uuid4
from sure import scenario, action_for

from goloka.app import app
from goloka.models import User, metadata, engine
from redis import StrictRedis
HTTPRETY_METHODS = [
    httpretty.GET,
    httpretty.POST,
    httpretty.PUT,
    httpretty.DELETE,
]


def GithubRepositoryStub(owner, name):
    return json.dumps(dict(name=name, owner=dict(login=owner)))


def setup_httpretty():
    httpretty.register_uri(
        httpretty.GET,
        re.compile('github.com/repos/\w+/\w+/languages'),
        body='[]',
        content_type='application/json')

    def repository_callback(method, uri, headers):
        return 200, {'server': 'Github'}, GithubRepositoryStub(*uri.strip("/").split("/")[-2:])

    httpretty.register_uri(
        httpretty.GET,
        re.compile('github.com/repos/([^/]+)/([^/]+)/?$'),
        body=repository_callback)


def prepare(context):
    setup_httpretty()

    conn = engine.connect()
    metadata.drop_all(engine)
    metadata.create_all(engine)
    conn.execute(User.table.delete())
    context.app = app.web.test_client()

    class FakeUser(User):
        api = Mock()

        def initialize(self):
            self.gb_token = 'abcd' * 10

    context.User = FakeUser

def prepare_redis(context):
    context.redis = StrictRedis()
    context.redis.flushall()

db_test = scenario([prepare])

def create_user(context):
    data = {
        "username": "octocat",
        "gravatar_id": "somehexcode",
        "email": "octocat@github.com",
        "github_token": 'toktok',
        "github_id": '123',
    }
    context.user = User.using(engine).create(**data)

user_test = scenario([prepare, create_user])
redis_test = scenario([prepare, create_user, prepare_redis])
