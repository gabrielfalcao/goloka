#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from goloka.workers.ec2 import SecurityGroupCreator
from goloka.workers.ec2 import InstanceCreator
from goloka.workers.s3 import StaticServeCreator

from Queue import Queue


class MachineCreators(object):
    def __init__(self):
        self.security_group_step1 = Queue()
        self.instance_to_create_step2 = Queue()
        self.assets_bucket_to_create_step3 = Queue()
        self.environments_done = Queue()

        self.workers = (
            ('security group creator', SecurityGroupCreator(self.security_group_step1, self.instance_to_create_step2)),
            ('instance creator', InstanceCreator(self.instance_to_create_step2, self.assets_bucket_to_create_step3)),
            ('static server creator', StaticServeCreator(self.assets_bucket_to_create_step3, self.environments_done)),
        )


    def start(self):
        for name, worker in self.workers:
            worker.start()

    def enqueue_build(self, instructions):
        self.security_group_step1.put(instructions)

    def wait_and_get_work(self):
        return self.environments_done.get()
