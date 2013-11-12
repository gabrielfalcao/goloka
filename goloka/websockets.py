#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import gevent
import random
import traceback
import json
import logging
from itertools import chain
from gevent.coros import Semaphore
from datetime import datetime
from socketio.namespace import BaseNamespace

log = logging.getLogger('goloka:websockets')


class Namespace(BaseNamespace):
    def humanized_now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def serialize(self, data):
        return json.dumps(data)

    def format_exception(self, exc):
        if exc:
            return traceback.format_exc(exc)

        return ''


class GolokaDashboard(Namespace):
    def on_save_build(self, md_token, build_info):
        log.info("Will save build %s", build_info)

        from goloka import db
        from goloka.models import User, Build
        log.info("Grabbing user by token %s", md_token)

        user = User.using(db.engine).find_one_by(md_token=md_token)

        log.info("Getting info")

        repository = build_info['repository']
        environment_name = build_info['environment_name']
        instance_type = build_info['instance_type']
        disk_size = build_info.get('disk_size', None) or '10'
        script = build_info.get('script')
        log.warning("Creating build %s", md_token)

        my_build = Build.create(
            user,
            environment_name=environment_name,
            instance_type=instance_type,
            disk_size=disk_size,
            repository=repository,
            script=script,
        )
        log.info("Build created %s", my_build)
        self.emit("build_saved", my_build.to_dict())

    def on_run_build(self, md_token, build_token):
        from goloka.models import Build
        my_build = Build.get_by_token(build_token)
        if my_build:
            my_build.run()
            log.info("Running build %s", my_build)

            self.emit("build_run_confirmed", my_build.to_dict())

        else:
            log.info("No build found for token %s", build_token)
            self.emit("unable_to_schedule_build", build_token)


NAMESPACES = {"": GolokaDashboard}
