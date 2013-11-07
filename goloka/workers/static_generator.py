#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys
import time
import logging
from boto import s3
from boto.exception import S3ResponseError
from boto.s3.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from goloka.workers.base import Worker

log = logging.getLogger('goloka:workers:s3')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class S3Worker(Worker):
    def get_connection(self):
        from goloka import settings
        return s3.connect_to_region(
            settings.AWS_DEFAULT_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def get_slug_for_name(self, name):
        return re.sub(r'\W+', '-', name)

class SecurityGroupCreator(S3Worker):
    def get_name_and_description(self, instructions):
        environment_name = instructions['environment_name']
        repository_name = instructions['repository']['full_name']
        description = '{0} - {1}: web + ssh open to the world'.format(environment_name, repository_name)
        name = ':goloka:'.join([environment_name, repository_name])
        return name, description

    def get_security_group(self, name):
        conn = self.get_connection()
        existing_groups = dict([(g.name, g) for g in conn.get_all_security_groups()])

        return existing_groups.get(name, None)

    def get_or_create_security_group(self, name, description):
        conn = self.get_connection()

        group = self.get_security_group(name)
        if not group:
            group = conn.create_security_group(name, description)

        return group

    def authorize_group(self, group, *args, **kw):
        try:
            group.authorize(*args, **kw)
        except S3ResponseError as e:
            if 'already' not in str(e).lower():
                self.log("Failed to authorize {0}{1} on group {2}: {3}".format(
                    args, kw, group.name, e
                ))

    def consume(self, instructions):
        conn = self.get_connection()
        name, description = self.get_name_and_description(instructions)

        group = self.get_or_create_security_group(name, description)

        self.authorize_group(group, 'tcp', 80, 80, '0.0.0.0/0')
        self.authorize_group(group, 'tcp', 22, 22, '0.0.0.0/0')
        self.authorize_group(group, 'tcp', 443, 443, '0.0.0.0/0')

        instructions['security_group'] = {
            'name': group.name,
            'description': group.description,
            'id': group.id,
            'rules': [
                {
                    'protocol': 'tcp',
                    'from_port': 80,
                    'to_port': 80,
                    'cidr_ip': '0.0.0.0/0',
                },
                {
                    'protocol': 'tcp',
                     'from_port': 443,
                    'to_port': 443,
                    'cidr_ip': '0.0.0.0/0',
                },                {
                    'protocol': 'tcp',
                    'from_port': 22,
                    'to_port': 22,
                    'cidr_ip': '0.0.0.0/0',
                },
            ]
        }
        self.produce(instructions)

    def rollback(self, instructions):
        conn = self.get_connection()
        name, description = self.get_name_and_description(instructions)
        group = self.get_security_group(name)
        if group and not group.instances():
            group.delete()


class StaticServeCreator(S3Worker):
    def consume(self, instructions):
        conn = self.get_connection()
        self.produce(instructions)

    def rollback(self, instructions):
        pass
