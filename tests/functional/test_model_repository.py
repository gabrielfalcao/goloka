#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from .base import redis_test
from goloka.models import Build


@redis_test
def test_build_create(context):
    ("Creating a build should create GPG key and store info in redis")

    # Given I create a build
    my_build = Build.create(
        context.user,
        environment_name='Production',
        instance_type='my-instance_type',
        disk_size=20,
        repository={
            'name': 'yipit_web',
            'full_name': 'Yipit/yipit_web',
            'owner': {
                'name': 'Yipit',
            },
        },
    )

    build_dict = my_build.to_dict()

    build_dict.should.have.key("environment_name").being.equal('Production')
    build_dict.should.have.key("machine_token").being.equal('68978e47c0841fcf9982aafd6dd150f0f5065991e38bca3cd34fc4b3651ce7ce457f7e4b7cd7a1b410fa82eb755776052c639fa8a9982c1d0e7c0586b87c87c6')
    build_dict.should.have.key("machine_specs").being.equal({
        'image_id': 'ami-ad184ac4',
        'instance_type': 'my-instance_type',
        'disk_size': 20,
        'assets_info': {
            'path': '/srv/static',
        },
    })
    build_dict.should.have.key("repository").being.equal({
            'name': 'yipit_web',
            'full_name': 'Yipit/yipit_web',
            'owner': {
                'name': 'Yipit',
            },
    })
    build_dict.should.have.key("gpg_fingerprint").being.a(basestring)
    build_dict.should.have.key("gpg_public_key").being.match("BEGIN PGP PUBLIC KEY BLOCK")
    build_dict.should_not.have.key("gpg_private_key")

    my_build.should.have.property("gpg_public_key").being.match("BEGIN PGP PUBLIC KEY BLOCK")
    my_build.should.have.property("gpg_private_key").being.match("BEGIN PGP PRIVATE KEY BLOCK")

    my_build.to_redis_payload().should.have.key("gpg_private_key").being.match("BEGIN PGP PRIVATE KEY BLOCK")

    build_info_raw = context.redis.hget('goloka:Yipit/yipit_web:builds', 'Production')
    build_info = json.loads(build_info_raw)
    build_info.should.equal(my_build.to_redis_payload())
