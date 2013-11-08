#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys
import time
import logging
from boto import ec2
from boto.exception import EC2ResponseError
from boto.ec2.blockdevicemapping import BlockDeviceMapping, BlockDeviceType
from goloka.workers.base import Worker
from goloka import settings

log = logging.getLogger('goloka:workers:ec2')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class EC2Worker(Worker):
    def serialize_instance(self, instance):
        types = (int, float, bool, type(None), str, unicode, dict, list, tuple, set)
        return dict([(k, getattr(instance, k)) for k in dir(instance) if not k.startswith('_') and isinstance(getattr(instance, k), types)])

    def get_connection(self):
        from goloka import settings
        return ec2.connect_to_region(
            settings.AWS_DEFAULT_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    @property
    def conn(self):
        if not hasattr(self, '__conn'):
            self.__conn = self.get_connection()

        return self.__conn

    def get_slug_for_name(self, name):
        return re.sub(r'\W+', '-', name).lower()

    def get_name_and_description(self, instructions):
        environment_name = instructions['environment_name']
        environment_slug = self.get_slug_for_name(environment_name)
        instructions['environment_slug'] = environment_slug

        repository_name = instructions['repository']['full_name']
        description = '{0} - {1}: web + ssh open to the world'.format(environment_name, repository_name)

        name = ':goloka:'.join([environment_slug, repository_name]).lower()
        return name, description

    def get_security_group(self, name):
        existing_groups = dict([(g.name, g) for g in self.conn.get_all_security_groups()])

        return existing_groups.get(name, None)

class SecurityGroupCreator(EC2Worker):
    def get_or_create_security_group(self, name, description):
        group = self.get_security_group(name)
        if not group:
            group = self.conn.create_security_group(name, description)

        return group

    def authorize_group(self, group, *args, **kw):
        try:
            group.authorize(*args, **kw)
        except EC2ResponseError as e:
            if 'already' not in str(e).lower():
                self.log("Failed to authorize {0}{1} on group {2}: {3}".format(
                    args, kw, group.name, e
                ))

    def consume(self, instructions):
        name, description = self.get_name_and_description(instructions)

        group = self.get_or_create_security_group(name, description)

        group.add_tag(name)
        self.authorize_group(group, 'tcp', 80, 80, '0.0.0.0/0')
        self.authorize_group(group, 'tcp', 22, 22, '0.0.0.0/0')
        self.authorize_group(group, 'tcp', 443, 443, '0.0.0.0/0')

        instructions['tag'] = name

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

    def after_consume(self, instructions):
        msg = "Security group ready: {security_group[name]}".format(**instructions)
        self.log(msg)

    def rollback(self, instructions):
        name, description = self.get_name_and_description(instructions)
        group = self.get_security_group(name)
        if group and not group.instances():
            group.delete()


class InstanceCreator(EC2Worker):
    def get_existing_instances(self, tag_name):
        reservations = self.conn.get_all_instances()
        result = []
        for reservation in reservations:
            for instance in reservation.instances:
                if tag_name in instance.tags and instance.state != 'terminated':
                    result.append(instance)

        return result

    def create_instances(self, instructions):
        instance_name = "{environment_name} for {repository[full_name]}".format(**instructions)
        instructions['instance_name'] = instance_name
        tag_name = instructions['tag']
        image_id = instructions['machine_specs']['image_id']
        instance_type = instructions['machine_specs']['instance_type']
        disk_size_in_gb = int(instructions['machine_specs']['disk_size'])
        security_group = instructions['security_group']['name']

        dev_sda1 = BlockDeviceType()

        bdm = BlockDeviceMapping()
        bdm['/dev/sda1'] = dev_sda1

        dev_sda1.size = disk_size_in_gb

        reservation = self.conn.run_instances(
            image_id=image_id,
            key_name=settings.AWS_KEYPAIR_NAME,
            instance_type=instance_type,
            user_data=self.get_bootstrap_script_for(instructions),
            security_groups=[security_group],
            monitoring_enabled=True,
            block_device_map=bdm)

        for instance in reservation.instances:
            instance.add_tag("Name", instance_name)
            instance.add_tag(tag_name)

        return reservation.instances

    def get_bootstrap_script_for(self, instructions):
        url = settings.absurl('/bin/ready/{machine_token}'.format(**instructions))
        dependencies = " ".join([
            'git-core',
            'python-pip',
            'python-gnupg',
            'supervisor',
            'python-dev',
            'libmysqlclient-dev',
            'mysql-client',
            'libxml2-dev',
            'libxslt1-dev',
            'libevent-dev',
            'libev-dev',
        ])
        script_header = "\n".join([
            '#!/bin/bash\n',
            'set -x',
            'apt-get update',
            'apt-get install -y {0}'.format(dependencies),
            'wget "{0}'
        ]).strip()

        extra = "\n".join(["echo '{key}' >> ~/.ssh/known_hosts".format(**key) for key in instructions['ssh_keys']])
        script = "{0}\n{1}\n{2}".format(script_header, extra, instructions['extra_script'])
        return script

    def consume(self, instructions):
        tag_name = instructions['tag']
        security_group = instructions['security_group']['name']

        instances = self.get_existing_instances(tag_name)
        if not instances:
            instances = self.create_instances(instructions)

        instructions['instances'] = [self.serialize_instance(i) for i in instances]
        # wait until machine is running and finally produce
        self.produce(instructions)

    def after_consume(self, instructions):
        total_instances = len(instructions['instances'])
        label = '{0} instance{1}'.format(total_instances, total_instances != 1 and 's' or '')
        msg = "EC2 {0} ready".format(label)
        self.log(msg)

    def rollback(self, instructions):
        sgname = instructions['security_group']['name']
        security_group = self.get_security_group(sgname)
        for instance in security_group.instances():
            instance.terminate()
