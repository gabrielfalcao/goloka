#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gevent
import random
import traceback
import json
from itertools import chain
from gevent.coros import Semaphore
from datetime import datetime
from socketio.namespace import BaseNamespace

from goloka import db
from goloka.models import User, Build


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
        user = User.using(db.engine).find_one_by(md_token=md_token)

        repository = build_info['repository']
        environment_name = build_info['environment_name']
        instance_type = build_info['instance_type']
        disk_size = build_info.get('disk_size', None) or '10'
        script = build_info.get('script')

        my_build = Build.create(
            user,
            environment_name=environment_name,
            instance_type=instance_type,
            disk_size=disk_size,
            repository=repository,
            script=script,
        )
        print "Build created", my_build
        self.emit("build_saved", my_build.to_dict())

    def on_run_build(self, md_token, build_token):
        my_build = Build.get_by_token(build_token)
        if my_build:
            my_build.run()
            print "Running build", my_build
            self.emit("build_run_confirmed", my_build.to_dict())

        else:
            print "No build found", build_token
            self.emit("unable_to_schedule_build", build_token)


NAMESPACES = {"": GolokaDashboard}
