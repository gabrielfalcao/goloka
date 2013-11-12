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
            log.info("socket.io handling %s", environ['PATH_INFO'])
            socketio_manage(environ, NAMESPACES)
            log.info("socket.io handled %s", environ['PATH_INFO'])
            return

        log.info("flask handling %s", environ['PATH_INFO'])
        return self.app.web(environ, start_response)

app = SocketIOApp(App.from_env())
