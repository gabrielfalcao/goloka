#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import traceback
from pprint import pformat
from threading import RLock, Thread
from redis import StrictRedis


class Heart(object):
    def __init__(self):
        self.lock = RLock()
        self.beat()

    def is_beating(self):
        return self._is_beating

    def stop(self):
        self._is_beating = False
        return self.lock.release()

    def beat(self):
        self.lock.acquire()
        self._is_beating = True


class Worker(Thread):
    def __init__(self, consume_queue, produce_queue):
        super(Worker, self).__init__()
        self.consume_queue = consume_queue
        self.produce_queue = produce_queue
        self.heart = Heart()
        self.daemon = True

    def log(self, message, *args):
        redis = StrictRedis()
        msg = message % args
        log.info(message, *args)
        redis.rpush("goloka:logs", json.dumps({'message': msg}))

    def consume(self, instructions):
        raise NotImplemented("You must implement the consume method by yourself")

    def produce(self, payload):
        return self.produce_queue.put(payload)

    def before_consume(self):
        pass


    def after_consume(self, instructions):
        pass

    def run(self):
        while self.heart.is_beating():
            self.before_consume()
            instructions = self.consume_queue.get()
            try:
                self.consume(instructions)
            except Exception as e:
                error = traceback.format_exc(e)
                self.log(error)
                self.produce({
                    'success': False,
                    'error': error
                })
                continue

            self.after_consume(instructions)
