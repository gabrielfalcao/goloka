#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys
import time
import logging
from boto import s3
from boto.exception import S3ResponseError
from boto.s3.connection import Location
from goloka.workers.base import Worker

log = logging.getLogger('goloka:workers:s3')
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler(sys.stdout))


class S3Worker(Worker):

    @property
    def conn(self):
        if not hasattr(self, '__conn'):
            self.__conn = self.get_connection()

        return self.__conn

    def get_connection(self):
        from goloka import settings
        return s3.connect_to_region(
            settings.AWS_DEFAULT_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

index_html = """
<html>
  <head><title>Index for {repository[full_name]}</title></head>
  <body><h2>Welcome to {repository[full_name]}</h2>
  <footer>goloka</footer>
  </body>
</html>"""

error_html = """
<html>
  <head><title>Error</title></head>
  <body><h2>Error in {repository[full_name]}</h2>
  <footer>goloka</footer>
  </body>
</html>"""


class StaticServeCreator(S3Worker):
    def get_bucket_name(self, instructions):
        name = "{environment_slug}.{repository[full_name]}".format(**instructions)
        return re.sub(r'[^a-zA-Z0-9-]+', '-', name).lower().strip('-')

    def get_bucket(self, instructions):
        bucket_name = self.get_bucket_name(instructions)
        bucket = self.conn.lookup(bucket_name)
        return bucket

    def get_or_create_bucket(self, instructions):
        bucket_name = self.get_bucket_name(instructions)
        bucket = self.get_bucket(instructions)
        if not bucket:
            bucket = self.conn.create_bucket(bucket_name,
                                             location=Location.USWest,
                                             policy='public-read')

        return bucket

    def consume(self, instructions):
        assets_info = instructions['machine_specs'].get('assets_info')
        if not isinstance(assets_info, dict):
            self.log("Ignoring static website creation for {repository[full_name]} {environment_name}".format(
                **instructions
            ))
            return

        bucket = self.get_or_create_bucket(instructions)

        index_key = bucket.new_key('index.html')
        index_key.content_type = 'text/html'
        index_key.set_contents_from_string(index_html, policy='public-read')

        error_key = bucket.new_key('error.html')
        error_key.content_type = 'text/html'
        error_key.set_contents_from_string(error_html, policy='public-read')

        config = bucket.configure_website('index.html', 'error.html')

        instructions['bucket'] = {
            'name': bucket.name,
            'domain': bucket.get_website_endpoint(),
        }
        self.produce(instructions)

    def rollback(self, instructions):
        bucket = self.get_bucket(instructions)
        if bucket:
            self.log("Rolling back creation of bucket {0}".format(bucket.name))
            bucket.delete()
