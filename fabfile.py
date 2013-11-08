# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import commands
from datetime import datetime
from os.path import dirname, abspath, join
from fabric.api import run, runs_once, put, sudo

LOCAL_FILE = lambda *path: join(abspath(dirname(__file__)), *path)

SOURCECODE_PATH = LOCAL_FILE('*')

@runs_once
def create():
    sudo("apt-get -q=2 update")
    dependencies = [
        'git-core',
        'python-pip',
        'python-gnupg',
        'supervisor',
        'redis-server',
        'python-dev',
        'libmysqlclient-dev',
        'mysql-client',
        'libxml2-dev',
        'libxslt1-dev',
        'libevent-dev',
        'libev-dev',
        'virtualenvwrapper',
    ]
    sudo("apt-get install -q=2 -y aptitude")
    sudo("aptitude install -q=2 -y {0}".format(" ".join(dependencies)))
    sudo("test -e /srv && rm -rf /srv/")
    sudo("mkdir -p /srv/")
    sudo("chown -R ubuntu.ubuntu /srv")
    sudo("chown -R ubuntu.ubuntu /var/log/goloka")
    sudo("chown -R ubuntu.ubuntu /etc/supervisor")
    sudo("chmod -R 400 /srv")
    sudo("chmod -R 400 /var/log/goloka")
    sudo("chmod -R 400 /etc/supervisor")


@runs_once
def deploy():
    now = datetime.now()
    release_path = '/srv/goloka'
    put(LOCAL_FILE('.conf', 'ssh', 'id_rsa*'), "~/.ssh/")
    run("chmod 600 ~/.ssh/id_rsa*")
    run("test -e {0} || git clone git@github.com:Yipit/goloka.git {0}".format(release_path))
    run("cd /srv/goloka && git fetch --prune")
    run("cd /srv/goloka && git reset --hard origin/master")
    run("cd /srv/goloka && git clean -df")
    run("cd /srv/goloka && git pull")
    run("test -e /srv/venv || virtualenv --no-site-packages --clear /srv/venv")
    run(now.strftime("mkdir -p /var/log/goloka/%Y-%m-%d-%H:%M"))
    sudo(now.strftime("mv -f /var/log/supervisor/*.log /var/log/goloka/%Y-%m-%d-%H:%M/"))

    put(LOCAL_FILE('.conf', 'sitecustomize.py.template'), "/srv/venv/lib/python2.7/sitecustomize.py")

    run("/srv/venv/bin/pip uninstall -y -q curdling || echo")
    run("/srv/venv/bin/pip install -q curdling")
    run("/srv/venv/bin/curd -l DEBUG --log-name=curdling --log-file=/var/log/goloka/curdling.log install -r /srv/goloka/requirements.txt")

    put(LOCAL_FILE('.conf', 'supervisor.http.conf'), "/etc/supervisor/conf.d/goloka-http.conf")
    put(LOCAL_FILE('.conf', 'supervisor.workers.conf'), "/etc/supervisor/conf.d/goloka-workers.conf")

    sudo("service supervisor stop")
    sudo("(ps aux | egrep supervisord | grep -v grep | awk '{ print $2 }' | xargs kill -9 2>&1>/dev/null) 2>&1>/dev/null || printf '\033[1;32mSupervisor is down\033[0m'")
    sudo("(ps aux | egrep gunicorn | grep -v grep | awk '{ print $2 }' | xargs kill -9 2>&1>/dev/null) 2>&1>/dev/null || printf '\033[1;32mGunicorn is down\033[0m'")
    sudo("service supervisor start")
