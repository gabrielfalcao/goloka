#!/usr/bin/env python
# -*- coding: utf-8 -*-
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from redis import Redis
from mock import patch
from goloka.testing import app
from sure import scenario
from flask import request, Request


def prepare_redis(context):
    context.redis = Redis()
    context.redis.flushall()


def prepare_app(context):
    class LocalTestClient(object):
        def __init__(self, app):
            self.app = app

        def __call__(self, environ, start_response):
            environ['REMOTE_ADDR'] = environ.get('REMOTE_ADDR', '10.123.42.254')
            environ['HTTP_REFERRER'] = environ.get('HTTP_REFERRER', 'http://facebook.com')
            return self.app(environ, start_response)

    context.old_wsgi_app = app.web.wsgi_app
    app.web.wsgi_app = LocalTestClient(app.web.wsgi_app)
    context.client = lambda: app.web.test_client()


def cleanup_app(context):
    app.web.wsgi_app = context.old_wsgi_app
