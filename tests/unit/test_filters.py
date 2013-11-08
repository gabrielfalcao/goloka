#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import time
from goloka.data.filters import VisitorFilter


def fake_visitor(remote_addr, time=None):
    import time as module
    return {
        "request": {
            "remote_addr": remote_addr,
        },
        "time": time or module.time(),
    }


def test_visitor_filter_by_ip():
    ("VisitorFilter#by_unique_by_ip() should return the visitors that are unique by ip")
    # Given some visitors
    visitors = [
        fake_visitor("10.10.10.10", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("10.10.10.10", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("30.30.30.30", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("20.20.20.20", 1381406401),  # 2013-10-10 - 12:00:00
        fake_visitor("10.10.10.10", 1381428001),  # 2013-10-10 - 18:00:00

        fake_visitor("10.10.10.10", 1382248801),  # 2013-10-20 - 06:00:00
        fake_visitor("20.20.20.20", 1382270401),  # 2013-20-20 - 12:00:00
        fake_visitor("20.20.20.20", 1382270401),  # 2013-20-20 - 12:00:00
        fake_visitor("10.10.10.10", 1382270401),  # 2013-10-20 - 12:00:00
        fake_visitor("10.10.10.10", 1382292001),  # 2013-10-20 - 18:00:00

        fake_visitor("20.20.20.20", 1383112801),  # 2013-20-30 - 06:00:00
        fake_visitor("30.30.30.30", 1383134401),  # 2013-30-30 - 12:00:00
        fake_visitor("20.20.20.20", 1383156001),  # 2013-20-30 - 18:00:00
    ]

    # When I filter them by ip
    uniques = VisitorFilter(visitors).by_unique_by_ip()

    # Then they should be uniques
    uniques.should.equal([
        fake_visitor("10.10.10.10", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("30.30.30.30", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("20.20.20.20", 1381406401),  # 2013-10-10 - 12:00:00
])
