#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from flask import url_for
from goloka import settings


def full_url_for(*args, **kw):
    return settings.absurl(url_for(*args, **kw))


def mailtoify(string):
    return string.replace(' ', '%20').replace('\n', '%0D%0A')


class RepoInfo(object):
    project = None
    owner = None
    matched = None
    regexes = [
        re.compile(r'github[.]com/(?P<owner>[^/]+)/(?P<project>[^/]+)'),
        re.compile(r'(?P<owner>[\w_-]+)[.]github.(?:io|com)/(?P<project>[^/]+)'),
    ]

    def __init__(self, uri):
        self.uri = uri

        for matched in filter(bool, [r.search(uri) for r in self.regexes]):
            self.matched = matched
            self.owner = matched.group('owner')
            self.project = matched.group('project')
            break

    def __nonzero__(self):
        return self.matched is not None

    def remount(self):
        return 'http://github.com/{0}/{1}'.format(self.owner, self.project)

    @property
    def bookmark_url(self):
        return full_url_for('.show_bookmark', owner=self.owner, project=self.project)

    def to_dict(self):
        return dict(
            owner=self.owner,
            project=self.project,
            url=self.remount()
        )


class KeyRing(object):
    @classmethod
    def for_user_project_stats_list(cls, username, project, kind='stats'):
        return "list:{kind}:github:{username}/{project}".format(**locals())


    @classmethod
    def for_user_project_name_set(cls, username):
        return "set:github:{username}".format(**locals())
