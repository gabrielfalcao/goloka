#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import wraps
from goloka import settings
from flask import redirect, render_template, session

from .functions import user_is_authenticated

def user_is_not_yipit():
    data = session.get('github_user_data', False)
    if not data:
        return True

    organizations = data['organizations']
    organization_names = [o['login'] for o in organizations]
    return 'Yipit' not in organization_names


def requires_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not user_is_authenticated():
            url = settings.absurl('login')
            return redirect(url)
        elif user_is_not_yipit():
            return render_template('only_for_yipisters.html', status=403)
        return f(*args, **kwargs)

    return decorated_function
