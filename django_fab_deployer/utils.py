# -*- encoding: utf-8 -*-
# ! python2

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import


def fab_arg_to_bool(val):
    if isinstance(val, basestring):
        return val.lower() == 'true'

    return False