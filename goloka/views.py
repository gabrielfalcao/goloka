#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import re
import time
import gevent
import json
import urllib2
from flask import (
    Blueprint,
    request,
    session,
    render_template,
    redirect,
    g,
    flash,
    Response,
    url_for,
)
import traceback
from goloka import settings
from goloka.api import GithubUser, GithubEndpoint, GithubRepository, GithubOrganization
from goloka.handy.decorators import requires_login
from goloka.handy.functions import user_is_authenticated
from goloka.models import User, Build
from goloka.log import logger
from goloka import db
from redis import Redis
from markment.fs import Node
from redis import StrictRedis
from goloka.queues import build_queue

mod = Blueprint('views', __name__)


def json_response(data, status=200):
    return Response(json.dumps(data), mimetype="text/json", status=int(status))


def error_json_response(message, status=200):
    return json_response({
        'success': False,
        'error': {
            'message': message
        }
    }, status=status)


@mod.before_request
def prepare():
    g.user = None


def add_message(message, error=None):
    if 'messages' not in session:
        session['messages'] = []

    session['messages'].append({
        'text': message,
        'time': time.time(),
        'alert_class': error is None and 'uk-alert-success' or 'uk-alert-danger',
        'error': error,
    })


def full_url_for(*args, **kw):
    return settings.absurl(url_for(*args, **kw))


def ssl_full_url_for(*args, **kw):
    return settings.sslabsurl(url_for(*args, **kw))


@mod.context_processor
def inject_basics():
    return dict(
        settings=settings,
        messages=session.pop('messages', []),
        github_user=session.get('github_user_data', None),
        json=json,
        user=g.user,
        len=len,
        full_url_for=full_url_for,
        ssl_full_url_for=ssl_full_url_for,
    )


@mod.route("/")
def index():
    if 'github_user_data' in session:
        return redirect(url_for('.dashboard'))

    return render_template('index.html')



@mod.route("/logout")
def logout():
    session.pop('github_user_data', '')
    return redirect('/')


@mod.route("/dashboard")
@requires_login
def dashboard():
    redis = StrictRedis()

    organizations = session['github_user_data']['organizations']
    docs_found = {}
    for name, info in redis.hgetall('goloka:ready').iteritems():
        docs_found[name] = json.loads(info)

    return render_template('dashboard.html', organizations=organizations, docs_found=docs_found)


@mod.route("/email")
@requires_login
def email():
    return render_template('email/thankyou.html')


@mod.route("/build/<token>")
@requires_login
def show_build(token):
    build = Build.get_by_token(token)
    return render_template('build.html', build=build)

@mod.route("/bin/dashboard/show-commits/<owner>/<name>.json")
@requires_login
def ajax_show_commits(owner, name):
    token = session['github_token']
    api = GithubRepository.from_token(token)
    repository = api.get(owner, name)
    commits = api.get_commits(owner, name)
    return json_response({
        'token': token,
        'repository': repository,
        'commits': commits,
    })


@mod.route("/bin/dashboard/repo-list/<owner>.json")
@requires_login
def ajax_dashboard_repo_list(owner):
    token = session['github_token']
    org = GithubOrganization.from_token(token)
    redis = StrictRedis()
    repositories_with_hooks = {}
    try:
        repositories_with_hooks = redis.hgetall("goloka:hooks")
    except Exception:
        logger.exception("Failed to hgetall goloka:hooks")

    all_repositories = org.get_repositories(owner)
    tracked_repositories = []
    untracked_repositories = []

    for repo in all_repositories:
        full_name = repo['full_name']
        ready = json.loads(repositories_with_hooks.get(full_name, 'false'))
        repo['ready'] = ready
        repo['not_ready'] = not repo['ready']
        if full_name in repositories_with_hooks:
            tracked_repositories.append(repo)
        else:
            untracked_repositories.append(repo)

    repositories = tracked_repositories + untracked_repositories
    repositories_by_name = dict([(r['full_name'], r) for r in repositories])

    return json_response({
        'repositories': repositories,
        'repositories_by_name': repositories_by_name,
    })


@mod.route("/bin/create/hook.json", methods=["POST"])
@requires_login
def create_hook():
    redis = StrictRedis()
    owner = request.form['repository[owner][login]']
    repository = request.form['repository[name]']
    full_name = request.form['repository[full_name]']
    user_md_token = g.user.md_token
    payload = {
        "full_name": full_name,
        "user_md_token": user_md_token,
        "url": full_url_for(".webhook", owner=owner, repository=repository, md_token=user_md_token),
    }
    redis.hset("goloka:hooks", full_name, json.dumps(payload))
    return json_response(payload)


@mod.route('/bin/<owner>/<repository>/<md_token>/hook', methods=["POST"])
def webhook(owner, repository, md_token):
    user = User.using(db.engine).find_one_by(md_token=md_token)
    if not user:
        logger.warning("token not found %s for %s/%s", md_token, owner, repository)

        return error_json_response("token not found", 404)

    try:
        instructions = json.loads(request.form['payload'])

        instructions['token'] = user.github_token
        instructions['clone_path'] = '/tmp/YIPIT_DOCS'
        build_queue.enqueue(instructions)

    except Exception as e:
        traceback.print_exc(e)

    return json_response({'cool': True})


@mod.route('/bin/ready/<token>')
def report_machine_ready(token):
    build = Build.get_by_token(token)
    msg = "The machine {0} just reported it's working for {1}".format(request.remote_addr, build.environment_name)
    print msg
    redis = StrictRedis()
    redis.rpush("goloka:logs", msg)
    return json_response(build.to_dict)


@mod.route("/robots.txt")
def robots_txt():
    Disallow = lambda string: 'Disallow: {0}'.format(string)
    return Response("User-agent: *\n{0}\n".format("\n".join([
        Disallow('/bin/*'),
        Disallow('/thank-you'),
    ])))


@mod.route("/500")
def five00():
    return render_template('500.html')


@mod.route("/.healthcheck")
def healthcheck():
    return render_template('healthcheck.html')


@mod.route("/.ok")
def ok():
    return Response('YES\n\r')


@mod.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@mod.route('/login')
def login():
    cb = settings.absurl('.sys/callback')
    return mod.github.authorize('user,repo')


def get_github_token(token=None):
    return session.get('github_token', token)  # might bug


def github_callback(token):
    from goloka.models import User
    next_url = request.args.get('next') or '/'
    if not token:
        logger.error(u'You denied the request to sign in.')
        return redirect(next_url)

    session['github_token'] = token

    github_user_data = GithubUser.fetch_info(token, skip_cache=True)

    github_user_data['github_token'] = token

    g.user = User.get_or_create_from_github_user(github_user_data)
    session['github_user_data'] = github_user_data
    gh_user = GithubUser.from_token(token)

    return redirect(next_url)

@mod.route("/bin/dashboard/manage-builds/<owner>/<repository>.json")
@requires_login
def ajax_manage_builds(owner, repository):
    full_name = "{0}/{1}".format(owner, repository)
    builds = Build.get_all_by_full_name(full_name).values()
    return render_template('manage-builds-modal.html', full_name=full_name, builds=builds)

@mod.route("/bin/dashboard/manage-machines/<owner>/<repository>.json")
@requires_login
def ajax_manage_machines(owner, repository):
    redis = StrictRedis()
    machines = map(json.loads, redis.smembers("goloka:{owner}/{repository}:machines".format(**locals())))
    return render_template('manage-machines-modal.html', machines=machines, owner=owner, repository_name=repository)
