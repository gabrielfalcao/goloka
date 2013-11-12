#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import wraps
from goloka import settings
from flask import redirect, render_template, session

from .functions import user_is_authenticated

def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not user_is_authenticated():
            url = settings.absurl('login')
            return redirect(url)

        return f(*args, **kwargs)

    return decorated_function
