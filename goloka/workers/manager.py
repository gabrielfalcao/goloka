#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from goloka.workers.downloader import GithubDownloader
from goloka.workers.static_generator import StaticGenerator

from Queue import Queue


class Manager(object):
    def __init__(self):
        self.to_download = Queue()
        self.to_generate = Queue()
        self.to_notify_when_ready = Queue()

        self.workers = (
            ('downloader', GithubDownloader(self.to_download, self.to_generate)),
            ('static generator', StaticGenerator(self.to_generate, self.to_notify_when_ready)),
        )

    def start(self):
        for name, worker in self.workers:
            worker.start()

    def enqueue_build(self, instructions):
        self.to_download.put(instructions)
