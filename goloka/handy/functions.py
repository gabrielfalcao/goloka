# -*- coding: utf-8 -*-
import math
import colorsys
from flask import session, g

from goloka import settings
from goloka.log import logger


def user_is_authenticated():
    from goloka import settings
    from goloka.models import User
    data = session.get('github_user_data', {})
    login = data.get('login')
    if not login:
        return False

    g.user = User.find_one_by(username=login)
    return True
