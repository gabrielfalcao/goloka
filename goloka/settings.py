# -*- coding: utf-8; mode: python -*-
from milieu import Environment

env = Environment()

from uuid import uuid4
from os.path import join, abspath, expanduser

LOCAL_PORT = 5000
PORT = env.get_int('PORT', LOCAL_PORT)

# READY TO DEPLOY
DEBUG = PORT is LOCAL_PORT
PRODUCTION = not DEBUG
TESTING = env.get('TESTING', False)

# Database connection URI
DATABASE = env.get('MYSQL_URI')


if not PRODUCTION:
    import os
    DATABASE = env.get('GOLOKA_DB', 'mysql://root@localhost/goloka')

# Static assets craziness
LOCAL_FILE = lambda *p: abspath(join(__file__, '..', *p))

SQLALCHEMY_DATABASE_URI = DATABASE

if DEBUG:  # localhost
    HOST = 'localhost'
    DOMAIN = '{0}:{1}'.format(HOST, PORT)
    GITHUB_CLIENT_ID = 'bae76639a0b0be1ba87f'
    GITHUB_CLIENT_SECRET = 'b48f447af184fdcd67e817769c4e309781f7ac6d'
    GIT_BIN_PATH = '/usr/local/bin/git'
    GPG_BIN = 'gpg'
else:
    HOST = env.get("HOST")
    DOMAIN = env.get("DOMAIN")
    GITHUB_CLIENT_ID = 'd92af7364bf699adae05'
    GITHUB_CLIENT_SECRET = 'dcd96a0a6985d3ae48f8893b0bbb87ead5c59776'
    GIT_BIN_PATH = '/usr/bin/git'
    GPG_BIN = '/usr/bin/gpg'

DOCUMENTATION_ROOT = LOCAL_FILE('static', 'docs')

SCHEMA = PORT == 443 and 'https://' or "http://"

absurl = lambda *path: "{0}{1}/{2}".format(SCHEMA, DOMAIN, "/".join(path).lstrip('/'))
sslabsurl = lambda *path: "{0}{1}/{2}".format("https://", DOMAIN, "/".join(path).lstrip('/'))
GITHUB_CALLBACK_URL = absurl('/.sys/callback')

RELEASE = env.get('RELEASE', uuid4().hex)
# Session key, CHANGE IT IF YOU GET TO THE PRODUCTION! :)
SECRET_KEY = RELEASE + '%F&G*&H(*ds3657d468f57g68h'

REDIS_URI = env.get_uri("REDIS_URI")


AUTH_USER = env.get("AUTH_USER", "")
AUTH_PASSWD = env.get("AUTH_PASSWD", "")
absurl = lambda *path: "{0}{1}/{2}".format(SCHEMA, DOMAIN, "/".join(path).lstrip('/'))

SSH_PUBLIC_KEY_PATH = LOCAL_FILE("..", ".conf", "ssh", "id_rsa.pub")
SSH_PUBLIC_KEY = open(SSH_PUBLIC_KEY_PATH).read()

AWS_ACCESS_KEY_ID="AKIAIXVW4NHYZUSUQAHQ"
AWS_SECRET_ACCESS_KEY="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"
AWS_DEFAULT_REGION="us-east-1"
AWS_KEYPAIR_NAME = 'goloka-deployer'
GNUPG_HOME = env.get('GNUPG_HOME', LOCAL_FILE('.gpg-keys'))
