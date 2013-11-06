#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import json
import shutil
import subprocess
import logging
from urlparse import urlsplit

from functools import partial
from tempfile import TemporaryFile
from os.path import dirname, abspath, join, expanduser, exists, relpath

from goloka import settings
from goloka.workers.base import Worker
from goloka.api import GithubEndpoint
from redis import StrictRedis

log = logging.getLogger('goloka:workers')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class LocalStem(object):
    # mode = "100644"
    # path = "README.md"
    # sha = "9b21a51f0ed2604c3000b82c8c76c505fe852565"
    # size = 3820 if type == "blob"
    # type = "blob" or "tree"
    # url = "https://api.github.com/.../git/blobs/9b21a51.."
    size = 0

    def __init__(self, stem, api):
        self.__dict__.update(stem)
        self.api = api
        self.redis = StrictRedis()
        self.is_tree = (self.type == 'tree')
        self.is_blob = (self.type == 'blob')
        self.children = []

    def fetch(self):
        path = urlsplit(self.url).path

        response = self.api.retrieve(path, skip_cache=True)
        reply = json.loads(response['response_data'])

        if self.is_tree:
            contents = reply['tree']
        elif self.is_blob:
            contents = reply['content'].decode(reply['encoding'])

        return reply, contents

    def create_directory(self, path):
        if not exists(path):
            os.makedirs(path)

    def create_blob(self, path, data):
        with open(path, 'wb') as f:
            f.write(data)

    def exists(self, destination):
        in_disk = os.path.exists(destination)
        is_file = in_disk and not os.path.isdir(destination)
        in_disk_size = is_file and os.stat(destination).st_size or 0
        return in_disk and in_disk_size == self.size

    def __repr__(self):
        return '<LocalStem path="{path}", type="{type}", sha="{sha}">'.format(**self.__dict__)

    def log(self, message, *args):
        msg = message % args
        log.info(message, *args)
        self.redis.rpush("goloka:logs", json.dumps({'message': msg}))

    def persist(self, root):
        destination = join(root, self.path)
        if self.is_blob and self.exists(destination):
            self.log("[LocalStem.persist] Ignoring existing %s %s", self.type.upper(), relpath(destination))
            return

        meta, contents = self.fetch()

        make_stem = partial(LocalStem, api=self.api)

        if self.is_tree:
            self.log("[LocalStem.persist] Creating Tree %s as %s", self.sha, relpath(destination))
            self.create_directory(destination)

            for kernel in map(make_stem, contents):
                self.log("[LocalStem.persist] Fetching subtrees of %s at %s", self.sha, relpath(destination))
                kernel.persist(destination)
                self.children.append(kernel)

        elif self.is_blob:
            self.log("[LocalStem.persist] Persisting blob %s as %s", self.sha, relpath(destination))
            self.create_blob(destination, contents)


class RepositoryFetcher(object):
    def __init__(self, api, clone_path):
        self.api = api
        self.clone_path = clone_path

        self.owner = None
        self.repository = None

    @property
    def destination(self):
        return join(*filter(bool, [self.clone_path, self.owner, self.repository]))

    def fetch(self, owner, repository, tree='HEAD'):
        self.owner = owner
        self.repository = repository
        self.grab_tree(tree)

    def api_path(self, prefix, *path):
        return "/{0}".format(join(prefix, self.owner, self.repository, *path).lstrip(os.sep))

    def grab_tree(self, tree):
        path = self.api_path('repos', 'git', 'trees', tree)
        response = self.api.retrieve(path, skip_cache=True)

        reply = json.loads(response['response_data'])
        print reply
        sha = reply.get('sha', None)
        if sha != tree:
            raise RuntimeError("reply got SHA {0} but expected {1}".format(sha, tree))

        make_stem = partial(LocalStem, api=self.api)
        if not exists(self.destination):
            os.makedirs(self.destination)
        for stem in map(make_stem, reply['tree']):
            stem.persist(self.destination)


class GithubDownloader(Worker):
    def consume(self, instructions):
        # token = instructions['github_token']

        repository = instructions['repository']
        token = instructions['token']
        repository_name = repository['name']
        owner = repository['owner']
        owner_name = owner['name']

        clone_path = instructions.get('clone_path', '/tmp/DOCS')
        destination_path = join(clone_path, owner_name, repository_name)

        api = GithubEndpoint(token)

        if not exists(clone_path):
            os.makedirs(clone_path)
        else:
            shutil.rmtree(clone_path, True)
        success = True
        try:
            fetcher = RepositoryFetcher(api, clone_path)
            fetcher.fetch(owner_name, repository_name)
        except Exception as e:
            success = False
        payload = {
            'success': success,
            'clone_path': clone_path,
            'destination_path': destination_path,
            'repository': repository,
            'token': token
        }

        self.produce(payload)
