#!/usr/bin/env python
# -*- coding: utf-8 -*-

from goloka.db import models
from goloka.models import User


def test_can_find_models():
    ("db.models should be hold all the declared models")

    models.should.have.key('User').being.equal(User)
