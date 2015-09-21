# coding=utf-8

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

__all__ = [
    'venv_run',
    'deploy',
    'backup',
    'update_python_tools',
    'restart'
]

import os
import json
from time import gmtime, strftime

from fabric.api import env
from fabric.context_managers import cd, settings
from fabric.contrib.console import confirm
from fabric.decorators import task
from fabric.operations import os, run, local
from fabric.utils import abort
from color_printer import colors

from .exceptions import InvalidConfiguration, MissingConfiguration

DEPLOYMENT_CONFIG_FILE = "deploy.json"
DEFAULT_SOURCE_BRANCH = "master"


def function_builder(target, options):
    def function(more_args=None):

        if "warn_on_deploy" in options and options["warn_on_deploy"]:
            if not confirm('Are you sure you want to work on *{0}* server?'.format(target.upper()), default=True):
                abort('Deployment cancelled')

        env.user = options["user"]
        env.hosts = [options["hosts"]]
        env.deploy_path = options["deploy_path"]
        env.project_name = options["project_name"]
        env.venv_path = options["venv_path"]
        env.celery_enabled = options["celery_enabled"]
        env.use_ssh_config = True
        env.source_branch = options.get('source_branch', DEFAULT_SOURCE_BRANCH)

        if "key_filename" in options:
            env.key_filename = os.path.normpath(options["key_filename"])

    return function


def get_tasks():
    try:
        with open(os.path.join(os.getcwd(), DEPLOYMENT_CONFIG_FILE), "r") as deploy_config_file:
            data = deploy_config_file.read()
    except IOError:
        raise MissingConfiguration(
            "Configuration file `{0}` was not found in `{1}`".format(DEPLOYMENT_CONFIG_FILE, os.getcwd())
        )

    try:
        deployment_data = json.loads(data)
    except ValueError as e:
        raise InvalidConfiguration(e.message)

    for target, options in deployment_data.items():
        yield target, task(name=target)(function_builder(target, options))
        __all__.append(target)
        globals()[target] = task(name=target)(function_builder(target, options))

    for fabric_task in [venv_run, deploy, backup, update_python_tools, restart, status]:
        yield fabric_task.__name__, fabric_task


get_tasks()


def venv_run(command_to_run):
    run('source %s' % env.venv_path + ' && ' + command_to_run)


@task
def deploy(upgrade=False, *args, **kwargs):
    local("python src/manage.py validate_templates")
    local("python src/manage.py check")

    with cd(env.deploy_path):
        # Create backup
        backup()

        # Source code
        colors.blue("Pulling from git")
        run('git reset --hard')
        run('git checkout {0}'.format(env.source_branch))
        run('git pull --no-edit origin {0}'.format(env.source_branch))

        # Dependencies
        colors.blue("Installing bower dependencies")

        with settings(warn_only=True):  # Bower may not be installed
            run('bower prune')  # Uninstalls local extraneous packages.
            run('bower %s --config.interactive=false' % ('update' if upgrade else 'install'))

        colors.blue("Installing pip dependencies")
        venv_run('pip install --no-input --exists-action=i -r requirements/production.txt --use-wheel %s' % (
            '--upgrade' if upgrade else ''))

        # Django tasks
        colors.blue("Running Django commands")
        venv_run('python src/manage.py collectstatic --noinput')
        venv_run('python src/manage.py migrate')
        venv_run('python src/manage.py compress')

        venv_run('python src/manage.py clearsessions')
        venv_run('python src/manage.py clear_cache')
        venv_run('python src/manage.py clean_pyc')
        venv_run('python src/manage.py compilemessages')

        restart()
        status()

        colors.green("Done.")


@task
def backup(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Creating backup")

        run("mkdir -p data/deployment_backup")

        now_time = strftime("%Y-%m-%d_%H.%M.%S", gmtime())
        venv_run(
            "python src/manage.py dumpdata --format json --all --indent=3 --output data/deployment_backup/%s-dump.json" % now_time)

        colors.green("Done.")


@task
def update_python_tools(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Updating Python tools")

        venv_run('easy_install --upgrade pip')
        venv_run('pip install --no-input --exists-action=i --use-wheel --upgrade setuptools wheel')

        colors.green("Done.")


@task
def restart(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Restarting Gunicorn")
        run('supervisorctl restart {0}:{0}_gunicorn'.format(env.project_name))

        if env.celery_enabled:
            colors.blue("Restarting Celery")

            run('supervisorctl restart {0}:{0}_celeryd'.format(env.project_name))
            run('supervisorctl restart {0}:{0}_celerybeat'.format(env.project_name))

        colors.green("Done.")


@task
def status(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Retrieving status")
        run('supervisorctl status | grep "{0}"'.format(env.project_name))

        colors.green("Done.")
