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
from socketio.mixins import BroadcastMixin
from redis import StrictRedis


class Namespace(BaseNamespace):
    def humanized_now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def serialize(self, data):
        return json.dumps(data)

    def format_exception(self, exc):
        if exc:
            return traceback.format_exc(exc)

        return ''

redis = StrictRedis()
class YipitDocsBroadcaster(Namespace, BroadcastMixin):
    def broadcast_status(self, text, error=None):
        traceback = self.format_exception(error)
        css_class = error and 'error' or 'success'

        payload = self.serialize({
            'text': text,
            'traceback': traceback,
            'ok': not error,
            'when': self.humanized_now(),
            'class': css_class
        })
        self.broadcast_event('status', payload)
        if error:
            gevent.sleep(30)

    def send_notifications(self):
        total = redis.llen("goloka:logs")
        log = "<br />\n".join(redis.lrange("goloka:logs", 0, total))
        notification = redis.lpop("goloka:notifications") or False
        if total or notification:
            self.broadcast_event("notification", {
                'notification': notification and json.loads(notification),
                'log': log,
            })

    def on_listen(self, *args, **kw):
        workers = [
            self.spawn(self.send_notifications),
        ]
        gevent.joinall(workers)



NAMESPACES = {"": YipitDocsBroadcaster}
