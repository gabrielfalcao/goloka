#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from goloka.data.aggregators import VisitorAggregator

fake_visitor = lambda country_code, time: {
    "geo": {
        "city": "Brooklyn",
        "region_name": "NY",
        "area_code": 718,
        "time_zone": "America/New_York",
        "dma_code": 501,
        "metro_code": "New York, NY",
        "country_code3": "USA",
        "latitude": 40.71109999999999,
        "postal_code": "11211",
        "longitude": -73.9469,
        "country_code": country_code,
        "country_name": "United States",
        "continent": "NA",
    },
    "time": time,
}


def test_visitor_aggregator_by_country():
    ("VisitorAggregator#by_country() should return the visitors grouped by country code")
    # Given some visitors
    visitors = [
        fake_visitor("US", 101),
        fake_visitor("US", 10),
        fake_visitor("US", 1001),
        fake_visitor("US", 1),
        fake_visitor("BR", 201),
        fake_visitor("BR", 20),
        fake_visitor("MX", 401),
    ]

    # When I aggreate them
    by_country = VisitorAggregator(visitors).by_country()

    # Then they should be grouped by country
    by_country.should.equal({
        "US": [
            fake_visitor("US", 1),
            fake_visitor("US", 10),
            fake_visitor("US", 101),
            fake_visitor("US", 1001),
        ],
        "BR": [
            fake_visitor("BR", 20),
            fake_visitor("BR", 201),
        ],
        "MX": [
            fake_visitor("MX", 401),
        ],
    })


def test_visitor_aggregator_by_day():
    ("VisitorAggregator#by_day() should return the visitors grouped by every 24-hours")
    # Given some visitors
    visitors = [
        fake_visitor("US", 1381384801),  # 2013-10-10 - 06:00:00
        fake_visitor("US", 1381406401),  # 2013-10-10 - 12:00:00
        fake_visitor("US", 1381428001),  # 2013-10-10 - 18:00:00

        fake_visitor("US", 1382248801),  # 2013-10-20 - 06:00:00
        fake_visitor("US", 1382270401),  # 2013-10-20 - 12:00:00
        fake_visitor("US", 1382292001),  # 2013-10-20 - 18:00:00

        fake_visitor("US", 1383112801),  # 2013-10-30 - 06:00:00
        fake_visitor("US", 1383134401),  # 2013-10-30 - 12:00:00
        fake_visitor("US", 1383156001),  # 2013-10-30 - 18:00:00
    ]

    # When I aggreate them
    by_day = VisitorAggregator(visitors).by_day()

    # Then they should be grouped by country
    by_day.keys().should.equal(["2013-10-10", "2013-10-20", "2013-10-30"])
    by_day.should.equal({
        "2013-10-10": [
            fake_visitor("US", 1381384801),  # 2013-10-10 - 06:00:00
            fake_visitor("US", 1381406401),  # 2013-10-10 - 12:00:00
            fake_visitor("US", 1381428001),  # 2013-10-10 - 18:00:00
        ],
        "2013-10-20": [
            fake_visitor("US", 1382248801),  # 2013-10-20 - 06:00:00
            fake_visitor("US", 1382270401),  # 2013-10-20 - 12:00:00
            fake_visitor("US", 1382292001),  # 2013-10-20 - 18:00:00
        ],
        "2013-10-30": [
            fake_visitor("US", 1383112801),  # 2013-10-30 - 06:00:00
            fake_visitor("US", 1383134401),  # 2013-10-30 - 12:00:00
            fake_visitor("US", 1383156001),  # 2013-10-30 - 18:00:00
        ],
    })
