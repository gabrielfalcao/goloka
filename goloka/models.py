# -*- coding: utf-8 -*-
import re
import gnupg
import ejson as json
import ejson.serializers
import hashlib
from datetime import datetime
# from werkzeug import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger('goloka.models')

from goloka.db import db, metadata, Model, engine
from goloka import settings
from redis import StrictRedis
from goloka.queues import build_queue

def slugify(string):
    return re.sub(r'\W+', '-', string.lower())


def now():
    return datetime.now()


class User(Model):
    table = db.Table('md_user', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('github_id', db.Integer, nullable=False, unique=True),
        db.Column('github_token', db.String(256), nullable=True),
        db.Column('gravatar_id', db.String(40), nullable=False, unique=True),
        db.Column('username', db.String(80), nullable=False, unique=True),
        db.Column('md_token', db.String(40), nullable=False, unique=True),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )

    def initialize(self):
        from goloka.api import GithubUser
        sha = hashlib.sha1()
        sha.update("goloka:")
        sha.update(self.username)
        self.md_token = sha.hexdigest()
        self.api = GithubUser.from_token(self.github_token)

    def __repr__(self):
        return '<User %r, token=%r>' % (self.username, self.md_token)

    def get_github_url(self):
        return "http://github.com/{0}".format(self.username)

    def list_repositories(self):
        return self.api.get_repositories(self.username)

    def get_keys(self):
        return self.api.get_keys()

    @classmethod
    def create_from_github_user(cls, data):
        login = data.get('login')
        fallback_email = "{0}@ec2-54-218-234-227.us-west-2.compute.amazonaws.com".format(login)
        email = data.get('email', fallback_email) or fallback_email

        instance = cls.create(
            username=login,
            github_id=data.get('id'),
            gravatar_id=data.get('gravatar_id'),
            email=email,
            github_token=data.get('github_token')
        )
        logger.info("user %d created: %s", instance.id, instance.email)
        return instance

    @classmethod
    def get_or_create_from_github_user(cls, data):
        login = data.get('login')
        instance = cls.find_one_by(username=login)
        fallback_email = "{0}@ec2-54-218-234-227.us-west-2.compute.amazonaws.com".format(login)

        if not instance:
            instance = cls.create_from_github_user(data)
        else:
            instance.github_token = data.get('github_token')
            instance.email = data.get('email', instance.email)
            instance.save()

        return instance

class Organization(Model):
    table = db.Table('md_organization', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('owner_id', db.Integer, nullable=False),
        db.Column('name', db.String(80), nullable=False),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('company', db.UnicodeText, nullable=True),
        db.Column('blog', db.UnicodeText, nullable=True),
        db.Column('avatar_url', db.UnicodeText, nullable=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )


class OrganizationUsers(Model):
    table = db.Table('md_organization_users', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('user_id', db.Integer, nullable=False),
        db.Column('organization_id', db.Integer, nullable=False),
    )

key_smith = gnupg.GPG(gnupghome=settings.GNUPG_HOME, gpgbinary=settings.GPG_BIN)

class Build(object):
    def __init__(self, environment_name, instance_type, repository, gpg_fingerprint, keys,
                 image_id='ami-ad184ac4', disk_size=10, assets_path='/srv/static', machine_token=None, extra_script=None):
        self.environment_name = environment_name
        self.repository = repository
        self.instance_type = instance_type
        self.image_id = image_id
        self.disk_size = disk_size
        self.assets_path = assets_path
        self.keys = keys
        self.gpg_fingerprint = gpg_fingerprint
        self.gpg_public_key = key_smith.export_keys(gpg_fingerprint, False)
        self.gpg_private_key = key_smith.export_keys(gpg_fingerprint, True)
        self.machine_token = machine_token or self.create_hash()
        self.extra_script = extra_script or ''

    def create_hash(self):
        sha = hashlib.sha512()
        sha.update("goloka:build")
        sha.update(self.environment_name)
        sha.update(self.repository['full_name'])
        return sha.hexdigest()

    def encrypt(self, data):
        return key_smith.encrypt(data, [self.gpg_fingerprint])

    def decrypt(self, data):
        return key_smith.decrypt(data)

    @classmethod
    def generate_key(Build, name, author_email):
        keygen_input = key_smith.gen_key_input(
            key_type="RSA",
            key_length=1024,
            name_real=slugify(name),
            name_comment="Key generated by goloka",
            name_email=author_email
        )
        key = key_smith.gen_key(keygen_input)
        return key

    def save(self):
        redis = StrictRedis()
        key = 'goloka:{full_name}:builds'.format(**self.repository)
        redis.hset(key, self.environment_name, json.dumps(self.to_redis_payload()))

        key = 'goloka:builds-by-token'
        redis.hset(key, self.machine_token, json.dumps(self.to_redis_payload()))

    def run(self):
        build_queue.enqueue(self.to_redis_payload())

    @classmethod
    def from_dict(Build, meta):
        environment_name = meta['environment_name']
        instance_type = meta['machine_specs']['instance_type']
        image_id = meta['machine_specs']['image_id']
        repository = meta['repository']
        gpg_fingerprint = meta['gpg_fingerprint']
        assets_path = meta['machine_specs']['assets_info']['path']
        disk_size = meta['machine_specs']['disk_size']
        machine_token = meta['machine_token']
        ssh_keys = meta['ssh_keys']
        return Build(environment_name, instance_type, repository, gpg_fingerprint, ssh_keys, image_id=image_id,
                     disk_size=disk_size, assets_path=assets_path, machine_token=machine_token)

    @classmethod
    def get_by_token(Build, token):
        redis = StrictRedis()
        key = 'goloka:builds-by-token'
        raw = redis.hget(key, token)
        if raw:
            return Build.from_dict(json.loads(raw))

    @classmethod
    def get_all_by_full_name(Build, full_name):
        redis = StrictRedis()
        key = 'goloka:{0}:builds'.format(full_name)
        raw = redis.hgetall(key)
        result = []
        for environment_name, raw_build_dictionary in raw.items():
            result.append((environment_name, Build.from_dict(json.loads(raw_build_dictionary))))

        return dict(result)

    @classmethod
    def create(Build, user, environment_name, instance_type, disk_size, repository, script=None):
        """takes a User instance + keyword args:
        """
        key_name = ":".join([environment_name, repository['full_name']])
        gpgkey = Build.generate_key(key_name, user.email)
        instance = Build(
            environment_name,
            instance_type,
            repository,
            gpgkey.fingerprint,
            image_id='ami-ad184ac4',
            disk_size=disk_size,
            assets_path='/srv/static',
            extra_script=script,
            keys=user.get_keys(),
        )
        instance.save()
        return instance

    def to_dict(self):
        return {
            'environment_name': self.environment_name,
            'machine_token': self.machine_token,
            'machine_specs': {
                'image_id': 'ami-ad184ac4',
                'instance_type': self.instance_type,
                'disk_size': self.disk_size,
                'assets_info': {
                    'path': '/srv/static',
                },
            },
            'repository': self.repository,
            'gpg_fingerprint': self.gpg_fingerprint,
            'gpg_public_key': self.gpg_public_key,
            'ssh_keys': self.keys,
            'extra_script': self.extra_script,
        }

    def to_redis_payload(self):
        payload = self.to_dict()
        payload['gpg_private_key'] = self.gpg_private_key
        return payload



# {
#   "login": "github",
#   "id": 1,
#   "url": "https://api.github.com/orgs/github",
#   "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#   "name": "github",
#   "company": "GitHub",
#   "blog": "https://github.com/blog",
#   "location": "San Francisco",
#   "email": "octocat@github.com",
#   "public_repos": 2,
#   "public_gists": 1,
#   "followers": 20,
#   "following": 0,
#   "html_url": "https://github.com/octocat",
#   "created_at": "2008-01-14T04:33:35Z",
#   "type": "Organization"
# }
