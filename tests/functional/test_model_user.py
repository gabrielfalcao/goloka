#!/usr/bin/env python
# -*- coding: utf-8 -*-
import httpretty
from .base import db_test, user_test
from goloka.models import User


@db_test
def test_user_signup(context):
    ("context.User.create(dict) should create a "
     "user in the database")
    data = {
        "username": "octocat",
        "gravatar_id": "somehexcode",
        "email": "octocat@github.com",
        "github_token": 'toktok',
        "github_id": '123',
    }
    created = User.create(**data)

    created.should.have.property('id').being.equal(1)
    created.should.have.property('username').being.equal("octocat")
    created.should.have.property('github_id').being.equal(123)
    created.should.have.property('github_token').being.equal('toktok')
    created.should.have.property('gravatar_id').being.equal('somehexcode')
    created.should.have.property('email').being.equal('octocat@github.com')
    created.should.have.property('md_token').being.length_of(40)


@db_test
def test_user_signup_get_or_create_if_already_exists(context):
    ("context.User.get_or_create(dict) should get"
     "user from the database if already exists")

    data = {
        "username": "octocat",
        "gravatar_id": "somehexcode",
        "email": "octocat@github.com",
        "github_token": 'toktok',
        "github_id": '123',
    }
    created = User.create(**data)
    got = User.get_or_create(**data)

    got.should.equal(created)


@db_test
def test_user_signup_get_or_create_doesnt_exist(context):
    ("context.User.get_or_create(dict) should get"
     "user from the database if it does not exist yet")
    context.User.api.get_starred.return_value = []
    data = {
        "username": "octocat",
        "gravatar_id": "somehexcode",
        "email": "octocat@github.com",
        "github_token": 'toktok',
        "github_id": '123',
    }
    created = User.create(**data)

    created.should.have.property('id').being.equal(1)
    created.should.have.property('username').being.equal("octocat")
    created.should.have.property('github_id').being.equal(123)
    created.should.have.property('github_token').being.equal('toktok')
    created.should.have.property('gravatar_id').being.equal('somehexcode')
    created.should.have.property('email').being.equal('octocat@github.com')
    created.should.have.property('md_token').being.length_of(40)


@db_test
def test_find_one_by(context):
    ("context.User.find_one_by(**kwargs) should fetch user from the database")

    data = {
        "username": "octocat",
        "gravatar_id": "somehexcode",
        "email": "octocat@github.com",
        "github_token": 'toktok',
        "github_id": '123',
    }

    original_user = User.create(**data)

    User.find_one_by(id=1).should.be.equal(original_user)
    User.find_one_by(username='octocat').should.be.equal(original_user)


@db_test
def test_find_one_by_not_exists(context):
    ("context.User.find_one_by(**kwargs) should return None if does not exist")

    User.find_one_by(username='octocat').should.be.none


@db_test
def test_find_many_by_not_exists(context):
    ("context.User.find_by(**kwargs) should return an empty list if does not exist")

    User.find_by(username='octocat').should.be.empty


@db_test
def test_find_by(context):
    ("context.User.find_by(**kwargs) should fetch a list of users from the database")

    data1 = {
        "username": "octocat",
        "github_id": 42,
        "gravatar_id": "somehexcode2",
        "email": "octocat@github.com",
        "github_token": "toktok",
    }

    data2 = {
        "username": "octopussy",
        "github_id": 88,
        "gravatar_id": "somehexcode1",
        "email": "octopussy@github.com",
        "github_token": "toktok",
    }

    original_user1 = User.create(**data1)
    original_user2 = User.create(**data2)

    User.find_by(github_token='toktok').should.be.equal([
        original_user2,
        original_user1
    ])
