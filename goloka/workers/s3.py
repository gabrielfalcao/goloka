#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
import logging

from goloka.workers.base import Worker

log = logging.getLogger('goloka:workers:s3')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class StaticServeCreator(Worker):
    def consume(self, instructions):
        self.produce(instructions)

    def rollback(self, instructions):
        # Delete security group
        pass
