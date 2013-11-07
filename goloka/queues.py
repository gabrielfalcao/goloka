#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import time
from redis import StrictRedis


class RedisQueue(object):
    def __init__(self, key):
        self.key = key

    def get_next(self):
        redis = StrictRedis()
        raw = redis.lpop(self.key)
        while not raw:
            time.sleep(0.5)
            raw = redis.lpop(self.key)

        return json.loads(raw)


    def enqueue(self, item):
        redis = StrictRedis()
        redis.rpush(self.key, json.dumps(item))


build_queue = RedisQueue('goloka:to-build')
