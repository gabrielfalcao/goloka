#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from datetime import datetime


class VisitorAggregator(object):
    def __init__(self, visitors):
        self.visitors = visitors

    def by_country(self):
        results = defaultdict(list)
        for v in sorted(self.visitors, key=lambda v: v['time']):
            geo = v.get('geo')
            if not isinstance(geo, dict):
                continue

            code = v['geo']['country_code']
            results[code].append(v)

        return dict(results)

    def by_day(self):
        results = defaultdict(list)
        for v in sorted(self.visitors, key=lambda v: v['time']):
            date = datetime.fromtimestamp(v['time'])
            day = date.strftime("%Y-%m-%d")
            results[day].append(v)

        return dict(results)
