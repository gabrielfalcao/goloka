#!/usr/bin/env python
# -*- coding: utf-8; -*-
import os
import sys
import time
import json

from datetime import datetime

from flask.ext.script import Command
from flask.ext.script import Command, Option
from redis import StrictRedis

LOGO = """
Y88b   d88P d8b              d8b   888
 Y88b d88P  Y8P              Y8P   888
  Y88o88P                          888
   Y888P    888   88888b.    888   888888
    888     888   888 '88b   888   888
    888     888   888  888   888   888
    888     888   888 d88P   888   Y88b.
    888     888   88888P'    888    'Y888
                  888
                  888
                  888

            8888888b.
            888  'Y88b
            888    888
            888    888 .d88b.  .d8888b.d8888b
            888    888d88''88bd88P'   88K
            888    888888  888888     'Y8888b.
            888  .d88PY88..88PY88b.        X88
            8888888P'  'Y88P'  'Y8888P 88888P'
"""

class RunWorkers(Command):
    def run(self):
        redis = StrictRedis()
        from goloka.workers.manager import Manager
        workers = Manager()
        workers.start()
        print "Waiting for a build..."

        while True:
            next_build_raw = redis.lpop("yipidocs:builds")
            if not next_build_raw:
                time.sleep(3)
                continue

            next_build = json.loads(next_build_raw)

            workers.enqueue_build(next_build)
            payload = workers.to_notify_when_ready.get()
            if 'error' in payload:
                sys.stderr.write(payload['error'])
                continue

            repository = payload['repository']
            owner = repository['owner']['name']
            serialized_payload = json.dumps(payload)
            full_name = "{owner[name]}/{name}".format(**repository)
            redis.hset("goloka:ready", full_name, serialized_payload)
            redis.rpush("goloka:notifications", json.dumps({
                'message': 'Documentation ready: {0}'.format(full_name)
            }))
            print "Waiting for a build..."


class EnqueueProject(Command):
    def run(self):
        from goloka.models import User
        from goloka import db
        redis = StrictRedis()
        users = User.using(db.engine).all()
        if not users:
            print "Run the server and log in with github, I need a real user token to test this..."
            raise SystemExit(1)
        user = users[0]

        redis.rpush("yipidocs:builds", json.dumps({
            'token': user.github_token,
            'clone_path': '/tmp/YIPIT_DOCS',
            'repository': {
                'name': 'yipit-client',
                'owner': {
                    'name': 'Yipit',
                }
            }
        }))

class Check(Command):
    def run(self):
        from goloka.app import App
        from goloka.settings import absurl
        from traceback import format_exc
        app = App.from_env()
        HEALTHCHECK_PATH = "/"
        try:
            print LOGO
            print "SMOKE TESTING APPLICATION"
            app.web.test_client().get(HEALTHCHECK_PATH)
        except Exception as e:
            print "OOPS"
            print "An Exception happened when making a smoke test to \033[1;37m'{0}'\033[0m".format(absurl(HEALTHCHECK_PATH))
            print format_exc(e)
            raise SystemExit(3)

def init_command_manager(manager):
    manager.add_command('enqueue', EnqueueProject())
    manager.add_command('check', Check())
    manager.add_command('workers', RunWorkers())
    return manager
