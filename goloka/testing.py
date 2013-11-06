# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from goloka.app import app

Client = lambda: app.web.test_client()
