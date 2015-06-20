# -*- encoding: utf-8 -*-
# ! python2

from __future__ import unicode_literals
from __future__ import print_function

import json
import os
import sys

from fabric.main import main as fabric_main


def write_example_config():
    deployment_options = {
        'example_production_host': {
            "deploy_path": "/var/www/SOME_PATH",
            "hosts": "8.8.8.8",
            "key_filename": "~/.ssh/SOME_PUBLIC_KEY",
            "user": "USER",
            "venv_path": "data/.venv/bin/activate",
            "warn_on_deploy": True,
            "celery_enabled": True,
            "project_name": "SOME_NAME"
        },
        'example_development_host': {
            "deploy_path": "/var/www/SOME_PATH",
            "hosts": "8.8.8.8",
            "key_filename": "~/.ssh/SOME_PUBLIC_KEY",
            "user": "USER",
            "venv_path": "data/.venv/bin/activate",
            "warn_on_deploy": False,
            "celery_enabled": False,
            "project_name": "SOME_NAME"
        }
    }

    with open(os.path.join(os.getcwd(), 'example.json'), mode="w+") as the_file:
        the_file.write(json.dumps(deployment_options, sort_keys=True, indent=2))


def main():
    if "write_example_config" in sys.argv:
        write_example_config()
        return 0

    this_dir = os.path.dirname(os.path.realpath(__file__))

    sys.argv = ['fab', '-f', os.path.join(this_dir, "fabfile.py")] + sys.argv[1:]
    fabric_main()


if __name__ == '__main__':
    main()
