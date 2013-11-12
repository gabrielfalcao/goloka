#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import logging
from goloka.app import App
from goloka import settings
from socketio import socketio_manage
from socketio.server import SocketIOServer

log = logging.getLogger('goloka:websockets')

class SocketIOApp(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        from goloka.websockets import NAMESPACES

        if environ['PATH_INFO'].startswith('/socket.io'):
            socketio_manage(environ, NAMESPACES)
            return

        return self.app.web(environ, start_response)

app = SocketIOApp(App.from_env())
from socketio.sgunicorn import GeventSocketIOWorker

class GunicornWorker(GeventSocketIOWorker):
    resource = 'socket.io'
    policy_server = False
