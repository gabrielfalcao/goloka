# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import commands
from datetime import datetime
from os.path import dirname, abspath, join
from fabric.api import run, runs_once, put

LOCAL_FILE = lambda *path: join(abspath(dirname(__file__)), *path)

SOURCECODE_PATH = LOCAL_FILE('*')

@runs_once
def create():
    now = datetime.now()
    run("apt-get -q=2 update")
    dependencies = [
        'git-core',
        'python-pip',
        'supervisor',
        'python-dev',
        'libmysqlclient-dev',
        'mysql-client',
        'redis-server',
        'libxml2-dev',
        'libxslt1-dev',
        'libevent-dev',
        'libev-dev',
        'virtualenvwrapper',
    ]
    run("apt-get install -q=2 -y aptitude")
    run("aptitude install -q=2 -y {0}".format(" ".join(dependencies)))
    run("test -e /srv && rm -rf /srv/")
    run("mkdir -p /srv/static")
    run(now.strftime("cp -rfv /var/log/supervisor /var/backups/supervisor-%Y-%m-%d"))
    run("rm -rf /var/log/supervisor")
    run("mkdir -p /var/log/supervisor")
    run("rm -rf ~/.curds")


@runs_once
def deploy():
    release_path = '/srv/goloka'
    put(LOCAL_FILE('.conf', 'ssh', 'id_rsa*'), "~/.ssh/")
    run("chmod 600 ~/.ssh/id_rsa*")
    run("test -e {0} || git clone git@github.com:Yipit/goloka.git {0}".format(release_path))
    run("cd /srv/goloka && git fetch --prune")
    run("cd /srv/goloka && git reset --hard origin/master")
    run("cd /srv/goloka && git clean -df")
    run("cd /srv/goloka && git pull")

    run("test -e /srv/venv || virtualenv --no-site-packages --clear /srv/venv")

    put(LOCAL_FILE('.conf', 'sitecustomize.py.template'), "/srv/venv/lib/python2.7/sitecustomize.py")

    run("/srv/venv/bin/pip install -U -q curdling")
    run("/srv/venv/bin/curd -l DEBUG --log-name=curdling --log-file=/var/log/curdling.log install -r /srv/goloka/requirements.txt")

    put(LOCAL_FILE('.conf', 'supervisor.http.conf'), "/etc/supervisor/conf.d/goloka-http.conf")
    put(LOCAL_FILE('.conf', 'supervisor.workers.conf'), "/etc/supervisor/conf.d/goloka-workers.conf")

    run("supervisorctl stop all")
    run("service supervisor stop")
    run("(ps aux | egrep python | grep -v grep | awk '{ print $2 }' | xargs kill -9 2>&1>/dev/null) 2>&1>/dev/null || printf '\033[0m'")
    run("service supervisor start")
