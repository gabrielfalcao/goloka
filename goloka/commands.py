#!/usr/bin/env python
# -*- coding: utf-8; -*-
import os
import sys
import time
import json

from datetime import datetime

from flask.ext.script import Command
from flask.ext.script import Command, Option
from redis import StrictRedis

LOGO = """
                  dP          dP
                  88          88
.d8888b. .d8888b. 88 .d8888b. 88  .dP  .d8888b.
88'  `88 88'  `88 88 88'  `88 88888'   88'  `88
88.  .88 88.  .88 88 88.  .88 88  `8b. 88.  .88
`8888P88 `88888P' dP `88888P' dP   `YP `88888P8
     .88
 d8888P
"""


class RunWorkers(Command):
    def run(self):
        redis = StrictRedis()
        from goloka.workers.manager import MachineCreators
        from goloka.queues import build_queue

        workers = MachineCreators()
        workers.start()

        while True:
            print "Waiting for a build..."
            next_build = build_queue.get_next()
            workers.enqueue_build(next_build)
            payload = workers.wait_and_get_work()
            if 'error' in payload:
                sys.stderr.write(payload['error'])
                continue

            print "Finished deploy:", payload


class EnqueueProject(Command):
    def run(self):
        from goloka.queues import build_queue

        # * t1.micro
        # * m1.small
        # * m1.medium
        # * m1.large
        # * m1.xlarge
        # * m3.xlarge
        # * m3.2xlarge
        # * c1.medium
        # * c1.xlarge
        # * m2.xlarge
        # * m2.2xlarge
        # * m2.4xlarge
        # * cr1.8xlarge
        # * hi1.4xlarge
        # * hs1.8xlarge
        # * cc1.4xlarge
        # * cg1.4xlarge
        # * cc2.8xlarge

        build_queue.enqueue({
            'environment_name': 'Production',
            'machine_specs': {
                'image_id': 'ami-ad184ac4',
                'instance_type': 't1.micro',
                'disk_size': 10,
                'bootstrap_script': '''#!/bin/bash
export IPADDRESS=`ifconfig eth0 | egrep "inet addr" | sed "s,[^0-9]*[:],," | sed "s, .*$,,g"`
curl -i -H "Accept: application/json" -X POST -d "ip_address=$IPADDRESS" http://ec2-54-218-234-227.us-west-2.compute.amazonaws.com/bin/ready
                '''
            },
            'repository': {
                'name': 'yipit_web',
                'full_name': 'Yipit/yipit_web',
                'owner': {
                    'name': 'Yipit',
                }
            }
        })


class Check(Command):
    def run(self):
        from goloka.app import App
        from goloka.settings import absurl
        from traceback import format_exc
        app = App.from_env()
        HEALTHCHECK_PATH = "/"
        try:
            print LOGO
            print "SMOKE TESTING APPLICATION"
            app.web.test_client().get(HEALTHCHECK_PATH)
        except Exception as e:
            print "OOPS"
            print "An Exception happened when making a smoke test to \033[1;37m'{0}'\033[0m".format(absurl(HEALTHCHECK_PATH))
            print format_exc(e)
            raise SystemExit(3)

def init_command_manager(manager):
    manager.add_command('check', Check())
    manager.add_command('workers', RunWorkers())
    manager.add_command('enqueue', EnqueueProject())
    return manager
