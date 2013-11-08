#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from datetime import datetime


class VisitorFilter(object):
    def __init__(self, visitors):
        self.visitors = visitors

    def by_unique_by_ip(self):
        seen = []
        result = []
        for req in self.visitors:
            ip = req['request']['remote_addr']
            if ip not in seen:
                result.append(req)
                seen.append(ip)

        return result
