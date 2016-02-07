# -*- encoding: utf-8 -*-
# ! python2

from __future__ import (absolute_import, division, print_function, unicode_literals)

import os


def fab_arg_to_bool(val):
    if isinstance(val, basestring):
        return val.lower() == 'true'

    return False


def find_file_in_path(filename_to_find, path_list):
    for dirname in path_list:
        candidate = os.path.join(dirname, filename_to_find)
        if os.path.isfile(candidate):
            return candidate

    return False
