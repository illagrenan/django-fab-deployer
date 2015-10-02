# coding=utf-8

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import json
from time import gmtime, strftime
import time

from colorclass import Color
import requests
from fabric.api import env
from fabric.context_managers import cd, settings
from fabric.contrib.console import confirm
from fabric.decorators import task
from fabric.operations import os, run, local
from fabric.utils import abort
from color_printer import colors
from terminaltables import SingleTable

from .exceptions import InvalidConfiguration, MissingConfiguration

__all__ = [
    'venv_run',
    'deploy',
    'backup',
    'update_python_tools',
    'restart'
]

DEPLOYMENT_CONFIG_FILE = "deploy.json"
DEFAULT_SOURCE_BRANCH = "master"


def _print_table(table):
    try:
        print(table.table)
    except UnicodeEncodeError:
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(table.table_data)


def _print_deployment_summary(env):
    table_data = [
        ["Project name:", env.project_name],
        ["Target:", env.target_name],
        ["User:", env.user],
        ["Host(s):", "; ".join(env.hosts)],
    ]

    table = SingleTable(table_data)
    table.title = Color('{autoyellow}Deployment configuration{/autoyellow}')
    table.justify_columns = {0: 'left', 1: 'left'}
    table.inner_row_border = False
    table.inner_heading_row_border = False

    _print_table(table)


def _print_simple_table(s):
    table = SingleTable([[Color('{autoblue}' + s + '{/autoblue}')]])
    _print_table(table)


def function_builder(target, options):
    def function(more_args=None):

        env.user = options["user"]
        env.hosts = [options["hosts"]]
        env.target_name = target
        env.deploy_path = options["deploy_path"]
        env.project_name = options["project_name"]
        env.venv_path = options["venv_path"]
        env.celery_enabled = options.get('celery_enabled', False)
        env.use_ssh_config = True
        env.source_branch = options.get('source_branch', DEFAULT_SOURCE_BRANCH)
        env.graceful_restart = options.get('graceful_restart', False)

        if "key_filename" in options:
            env.key_filename = os.path.normpath(options["key_filename"])

        env.urls_to_check = options["urls_to_check"] if "urls_to_check" in options else []

        _print_deployment_summary(env)

        if "warn_on_deploy" in options and options["warn_on_deploy"]:
            if not confirm('Are you sure you want to work on *{0}* server?'.format(target.upper()), default=True):
                abort('Deployment cancelled')

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

    for fabric_task in [venv_run,
                        deploy,
                        backup,
                        update_python_tools,
                        restart,
                        graceful_restart,
                        status,
                        check,
                        clean,
                        check_urls,
                        npm,
                        gulp]:
        yield fabric_task.__name__, fabric_task


get_tasks()


def venv_run(command_to_run):
    run('source %s' % env.venv_path + ' && ' + command_to_run)


@task
def deploy(upgrade=False, *args, **kwargs):
    start = time.time()

    _print_simple_table('Deployment started')

    if isinstance(upgrade, basestring):
        upgrade = upgrade.lower() == 'true'

    check()

    with cd(env.deploy_path):
        # Create backup
        backup()

        # Source code
        colors.blue("Pulling from git")
        run('git reset --hard')
        run('git checkout {0}'.format(env.source_branch))
        run('git pull --no-edit origin {0}'.format(env.source_branch))

        # Dependencies
        npm(upgrade)

        # Dependencies
        colors.blue("Installing bower dependencies")

        with settings(warn_only=True):  # Bower may not be installed
            run('bower prune')  # Uninstalls local extraneous packages.
            run('bower %s --config.interactive=false' % ('update' if upgrade else 'install'))

        gulp()

        colors.blue("Installing pip dependencies")
        venv_run('pip install --no-input --exists-action=i -r requirements/production.txt --use-wheel %s' % (
            '--upgrade' if upgrade  else ''))

        # Django tasks
        colors.blue("Running Django commands")
        venv_run('python src/manage.py collectstatic --noinput')
        venv_run('python src/manage.py migrate')
        venv_run('python src/manage.py compress')

        clean()

        venv_run('python src/manage.py compilemessages')

    graceful_restart() if env.graceful_restart else restart()

    status()
    check_urls()

    total_time_msg = "Deployed :)\nTotal time: {0} seconds.".format(time.time() - start)
    _print_simple_table(total_time_msg)


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
def npm(upgrade=False, *args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Installing node_modules")

        run("npm prune")
        run("npm install")

        if upgrade:
            run("npm update")

    colors.green("Done.")


@task
def clean(upgrade=False, *args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Cleaning Django project")

        venv_run('python src/manage.py clearsessions')
        venv_run('python src/manage.py clear_cache')
        venv_run('python src/manage.py clean_pyc --optimize --path=.')

        venv_run('python src/manage.py compile_pyc --path=.')

    colors.green("Done.")


@task
def gulp(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Starting gulp build")

        run("gulp clean")
        run("gulp build --production")

    colors.green("Done.")


@task
def check_urls(*args, **kwargs):
    logging.basicConfig(level=logging.DEBUG)

    for url in env.urls_to_check:
        print("Checking `{0}`".format(url))
        r = requests.get(url)
        if r.status_code != 200: abort("HTTP status for `{0}` is `{1}`.".format(url, r.status_code))

    colors.green("Done.")


@task
def update_python_tools(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Updating Python tools")

        venv_run('easy_install --upgrade pip')
        venv_run('pip install --no-input --exists-action=i --use-wheel --upgrade setuptools wheel')

    colors.green("Done.")


@task
def check(*args, **kwargs):
    colors.blue("Checking local project")

    with settings(warn_only=True):
        local("git status --porcelain")

    local("python src/manage.py check")
    local("python src/manage.py validate_templates")

    colors.green("Done.")


@task
def restart(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Restarting Gunicorn")
        run('supervisorctl restart {0}:{0}_gunicorn'.format(env.project_name))

        # pid videmi_eu:videmi_eu_gunicorn | xargs kill -s HUP

        if env.celery_enabled:
            colors.blue("Restarting Celery")

            run('supervisorctl restart {0}:{0}_celeryd'.format(env.project_name))
            run('supervisorctl restart {0}:{0}_celerybeat'.format(env.project_name))

    colors.green("Done.")


@task
def graceful_restart(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Restarting Gunicorn with HUP signal")
        run('pid {0}:{0}_gunicorn | xargs kill -s HUP'.format(env.project_name))

        if env.celery_enabled:
            colors.blue("Restarting Celery with HUP signal")

            run('pid {0}:{0}_celeryd | xargs kill -s HUP'.format(env.project_name))
            run('pid {0}:{0}_celerybeat | xargs kill -s HUP'.format(env.project_name))

    colors.green("Done.")


@task
def status(*args, **kwargs):
    with cd(env.deploy_path):
        colors.blue("Retrieving status")

        run('supervisorctl status | grep "{0}"'.format(env.project_name))
        run('service nginx status')
        run('service mysql status')

    colors.green("Done.")
