#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import json
import logging
import subprocess
from tempfile import TemporaryFile
import os
from os.path import dirname, abspath, join, expanduser, exists
from markment.core import Project
from markment.fs import Generator, Node
from markment.ui import Theme, InvalidThemePackage

from goloka import settings
from goloka.workers.base import Worker
from markment.plugins import sitemap
from markment.plugins import autoindex

log = logging.getLogger('goloka:workers')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class StaticGenerator(Worker):
    def consume(self, instructions):
        if not instructions['success']:
            return self.produce(instructions)

        destination_path = instructions['destination_path']
        markment_yml_nodes = Node(destination_path).grep('[.]markment.yml')
        if not markment_yml_nodes:
            payload = {
                'success': False,
                'error': 'No .markment.yml found in the project {repository[name]}'.format(**instructions)
            }
            return self.produce(payload)

        markment_node = markment_yml_nodes[0].parent
        project = Project.discover(markment_node.path)
        theme_path = project.meta['project'].get('theme')

        if theme_path:
            theme_node = project.node.cd(theme_path)
            theme = Theme.load_from_path(theme_node.path)
        else:
            theme = Theme.load_by_name('slate')


        destination = Generator(project, theme)
        repository = instructions['repository']
        owner = repository['owner']['name']
        name = repository['name']
        static_destination = join(settings.DOCUMENTATION_ROOT, owner, name).format(project.name)

        generated = destination.persist(static_destination)

        documentation_root_node = Node(settings.DOCUMENTATION_ROOT)
        payload = {
            'documentation_path': static_destination,
            'repository': repository,
            'index': [documentation_root_node.relative(path) for path in generated],
        }
        log.info("Done generating %s", json.dumps(payload, indent=2))
        self.produce(payload)
