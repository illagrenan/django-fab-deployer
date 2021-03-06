# -*- encoding: utf-8 -*-
# ! python2

from __future__ import (absolute_import, division, print_function, unicode_literals)

import json
import logging
import os
import sys
import tempfile
import time
from time import gmtime, strftime

import environ
import requests

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from colorama import init, Fore, Back, Style
from fabric.api import env
from fabric.api import get
from fabric.context_managers import cd, settings, hide, shell_env, lcd
from fabric.contrib.console import confirm
from fabric.contrib.project import rsync_project
from fabric.decorators import task, runs_once
from fabric.network import needs_host
from fabric.operations import os, run, local
from fabric.utils import abort

from .exceptions import InvalidConfiguration, MissingConfiguration, FabricException
from .utils import fab_arg_to_bool, find_file_in_path

__all__ = []

DEPLOYMENT_CONFIG_FILE = "deploy.json"
DEFAULT_SOURCE_BRANCH = "master"

init(autoreset=True)


def _print_table(table):
    try:
        print(table.table)
    except UnicodeEncodeError:
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(table.table_data)


def _print_deployment_summary(env):
    print(Fore.YELLOW + "- - - - - - - - - - - - - - - - - - - -")
    print(Fore.YELLOW + "Deployment configuration")
    print(Fore.YELLOW + "- - - - - - - - - - - - - - - - - - - -")

    print('{0:<10} {1:<8}'.format("Name:", env.project_name))
    print('{0:<10} {1:<8}'.format("Target:", env.target_name))
    print('{0:<10} {1:<8}'.format("User:", env.user))
    print('{0:<10} {1:<8}'.format("Host(s):", "; ".join(env.hosts)))

    print(Fore.YELLOW + "- - - - - - - - - - - - - - - - - - - -")


def function_builder(target, options):
    def function(more_args=None):

        env.user = options["user"]
        env.hosts = [options["hosts"]]
        env.target_name = target
        env.deploy_path = options["deploy_path"]
        env.project_name = options["project_name"]
        env.supervisor_program = options["supervisor_program"] if "supervisor_program" in options else env.project_name
        env.db_name = options["db_name"] if "db_name" in options else env.project_name
        env.venv_path = options["venv_path"]
        env.celery_enabled = options.get('celery_enabled', False)
        env.celery_workers = options.get('celery_workers', [])
        env.huey_enabled = options.get('huey_enabled', False)
        env.opbeat_enabled = options.get('opbeat_enabled', False)

        if env.opbeat_enabled:
            env.opbeat_authorization_bearer = options.get('opbeat_authorization_bearer')
            env.opbeat_organization_id = options.get('opbeat_organization_id')
            env.opbeat_app_id = options.get('opbeat_app_id')

        env.yarn_enabled = options.get('yarn_enabled', False)
        env.celerybeat_enabled = options.get('celerybeat_enabled', False)
        env.clear_cache = options.get('clear_cache', True)
        env.backup_db = options.get('backup_db', True)
        env.db_engine = options.get('db_engine', 'postgresql')
        env.pytest = options.get('pytest', False)
        env.compress_enabled = options.get('compress_enabled', True)
        env.extra_databases = options["extra_databases"] if "extra_databases" in options else []
        env_to_export = options["export_env"] if "export_env" in options else {}
        env.export_env = env_to_export
        env.use_ssh_config = False
        env.source_branch = options.get('source_branch', DEFAULT_SOURCE_BRANCH)
        env.graceful_restart = options.get('graceful_restart', False)

        if "key_filename" in options:
            path_to_key = os.path.normpath(os.path.expanduser(options["key_filename"]))

            if not os.path.isfile(path_to_key):
                abort("{0} is not a file".format(path_to_key))

            env.key_filename = path_to_key

        env.urls_to_check = options["urls_to_check"] if "urls_to_check" in options else []
        env.urls_to_check_verify_ssl_certificate = options.get('urls_to_check_verify_ssl_certificate', True)

        _print_deployment_summary(env)

        if "warn_on_deploy" in options and options["warn_on_deploy"]:
            if not confirm('Are you sure you want to work on *{0}* server?'.format(target.upper()), default=True):
                abort('Deployment cancelled')

    return function


def get_tasks():
    path_list_to_search = [
        # Current directory
        os.getcwd(),
        # Parent directory
        os.path.abspath(os.path.join(os.getcwd(), os.pardir))
    ]

    deploy_config_file_path = find_file_in_path(DEPLOYMENT_CONFIG_FILE, path_list_to_search)

    if deploy_config_file_path:
        with open(deploy_config_file_path, "r") as deploy_config_file:
            data = deploy_config_file.read()
    else:
        raise MissingConfiguration(
            "Configuration file `{0}` was not found in `{1}`".format(DEPLOYMENT_CONFIG_FILE, path_list_to_search)
        )

    try:
        deployment_data = json.loads(data)
    except ValueError as e:
        raise InvalidConfiguration("Cannot load your deployment configuration. JSON file is probably broken. Additional message: %s" % e.message)

    for target, options in deployment_data.items():
        yield target, task(name=target)(function_builder(target, options))
        __all__.append(target)
        globals()[target] = task(name=target)(function_builder(target, options))

    for fabric_task in [venv_run,
                        deploy,
                        backup,
                        update_python_tools,
                        stop,
                        start,
                        restart,
                        graceful_restart,
                        kill,
                        kill_celery,
                        status,
                        check,
                        clean,
                        check_urls,
                        npm,
                        get_media,
                        rebuild_staticfiles,
                        rebuild_virtualenv,
                        get_dumps,
                        dump_db,
                        drop_schema,
                        shell_plus,
                        migrate,
                        manage,
                        pull,
                        pip_install,
                        register_deployment,
                        gulp]:
        yield fabric_task.__name__, fabric_task


get_tasks()


def venv_run(command_to_run):
    run('source %s' % env.venv_path + ' && ' + command_to_run)


@task
@needs_host
def deploy(upgrade=False, skip_npm=False, skip_check=False, *args, **kwargs):
    with shell_env(**env.export_env):
        start_ = time.time()

        print(Back.GREEN + 'Deployment started')

        upgrade = fab_arg_to_bool(upgrade)
        skip_npm = fab_arg_to_bool(skip_npm)
        skip_check = fab_arg_to_bool(skip_check)

        if not skip_check:
            check()
        else:
            print(Fore.YELLOW + "CHECK skipped!")

        with cd(env.deploy_path):
            if env.backup_db:
                dump_db()
            else:
                print(Fore.YELLOW + "Database was not backed up!")

            pull()

            if env.yarn_enabled:
                yarn()
            else:
                if not skip_npm:
                    npm(upgrade=upgrade)
                else:
                    print(Fore.YELLOW + "NPM skipped!")

            # Dependencies
            print(Fore.BLUE + "Installing bower dependencies")

            with settings(warn_only=True):  # Bower may not be installed
                run('bower prune --config.interactive=false')  # Uninstalls local extraneous packages.
                run('bower %s --config.interactive=false' % ('update' if upgrade else 'install'))

            gulp()
            pip_install(upgrade, *args, **kwargs)

            # Django tasks
            print(Fore.BLUE + "Running Django commands")
            venv_run('python src/manage.py collectstatic --noinput')

            migrate()

            if env.compress_enabled:
                venv_run('python src/manage.py compress')

            clean()

            # with cd('src/'):
            venv_run('cd src && python manage.py compilemessages')

            venv_run("python src/manage.py check --deploy")

        graceful_restart() if env.graceful_restart else restart()

    status()
    check_urls()

    if env.opbeat_enabled:
        register_deployment()

    print(Fore.GREEN + "- - - - - - - - - - - - - - - - - - - -")
    print(Fore.GREEN + Style.BRIGHT + "Deployed :-)")
    print(Fore.GREEN + "- - - - - - - - - - - - - - - - - - - -")
    print('{0:<10} {1:>8} seconds'.format("Total time:", int(time.time() - start_)))
    print(Fore.GREEN + "- - - - - - - - - - - - - - - - - - - -")


@task
def migrate(*args, **kwargs):
    with shell_env(**env.export_env):
        with cd(env.deploy_path):
            print(Fore.BLUE + "Migrating database")

            venv_run('python src/manage.py migrate --noinput')

            if env.extra_databases:
                for one_db in env.extra_databases:
                    venv_run('python src/manage.py migrate --noinput --database {db}'.format(db=one_db))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def pull(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Pulling from git")

        run('git reset --hard')
        run('git checkout {0}'.format(env.source_branch))
        run('git pull --no-edit origin {0}'.format(env.source_branch))
        run('git submodule update --quiet --recursive')

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def pip_install(upgrade=False, *args, **kwargs):
    upgrade = fab_arg_to_bool(upgrade)

    with cd(env.deploy_path):
        print(Fore.BLUE + "Installing pip dependencies")

        venv_run('pip install --no-input --compile --exists-action=i --use-wheel %s -r requirements/production.txt' % ('--upgrade' if upgrade  else ''))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def backup(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Creating backup")

        run("mkdir -p data/deployment_backup")

        now_time = strftime("%Y-%m-%d_%H.%M.%S", gmtime())

        venv_run("python src/manage.py dumpdata --format json --all --indent=3 --output data/deployment_backup/%s-dump.json" % now_time)

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def shell_plus(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Running IPython")

        venv_run("python src/manage.py shell_plus")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def manage(command, *args, **kwargs):
    with shell_env(**env.export_env):
        with cd(env.deploy_path):
            print(Fore.BLUE + "Running Django management command")

            venv_run("python src/manage.py {command}".format(command=command.strip()))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='dumpdb')
def dump_db(out_format='custom', *args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Dumping database")

        now_time = strftime("%Y-%m-%d_%H.%M.%S", gmtime())

        with settings(abort_exception=FabricException):
            if env.db_engine == 'postgresql':
                dump_postgres(env, now_time, out_format)
            elif env.db_engine == 'mysql':
                dump_mysql(env, now_time)
            else:
                print('Unsupported DB engine')
                sys.exit(1)

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='drop')
def drop_schema(*args, **kwargs):
    with settings(user='root'):
        if not confirm('This will DESTROY database schmema on the server!', default=False):
            abort('Drop cancelled.')

        with cd(env.deploy_path):
            print(Fore.RED + "Dropping database schema")

            run('whoami')
            run("sudo -u postgres psql --dbname={db_name} "
                "-c \"DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO postgres; GRANT ALL ON SCHEMA public TO public;\"".format(db_name=env.db_name))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


def dump_mysql(env, now_time):
    try:
        run("mysqldump --databases {0} > data/backup/{0}_{1}.sql".format(env.project_name, now_time))
    except FabricException:
        print("Hint: create configuration file with nano ~/.my.cnf")
        print("[client]" + os.linesep +
              "user = {}".format(env.project_name) + os.linesep +
              "password = xxx" +
              os.linesep +
              "host = 127.0.0.1")


def dump_postgres(env, now_time, out_format):
    try:
        extension = 'sql' if out_format == 'plain' else 'backup'
        dump_filename = "{project_name}_{now_time}.{extension}".format(project_name=env.project_name, now_time=now_time, extension=extension)

        # User `--inserts` to user INSERT INTO rather than COPY
        run("pg_dump "
            "--format={out_format} "  # plain || custom
            "--dbname={db_name} "
            "--encoding=utf8 "
            "--verbose "
            "--schema=public "
            "--clean "  # Drop all DB objects; only applied when out_format == plain
            "-f data/backup/{dump_filename}".format(out_format=out_format, db_name=env.db_name, dump_filename=dump_filename))

        if out_format == 'custom':
            print(Fore.GREEN + Style.BRIGHT + "Restore me with: `pg_restore {dump_filename} "
                                              "--clean "
                                              "--exit-on-error "
                                              "--format={out_format} "
                                              "--jobs=2 "
                                              "--verbose "
                                              "-n public "  # Restore only public schema
                                              "--dbname={db_name} "
                                              "[--data-only][--schema-only]`".format(out_format=out_format, dump_filename=dump_filename, db_name=env.db_name))
        else:
            print(Fore.GREEN + Style.BRIGHT + "Restore me with: `psql --file={dump_filename} "
                                              "--dbname={db_name}`".format(out_format=out_format, dump_filename=dump_filename, db_name=env.db_name))

    except FabricException:
        print("Hint: create configuration file with nano ~/.pgpass")
        print("# hostname:port:database:username:password" + os.linesep +
              "*:*:{0}:{0}:xxx".format(env.project_name))
        sys.exit(1)


@task
def get_media(delete=False, *args, **kwargs):
    delete = fab_arg_to_bool(delete)

    with cd(env.deploy_path):
        print(Fore.BLUE + "Rsyncing local media with remote")

        rsync_project(local_dir='data/',
                      remote_dir="{0}/data/media".format(env.deploy_path.rstrip("/")),
                      exclude=['.git*', 'cache*', 'filer_*'],
                      delete=delete,
                      ssh_opts="-o UserKnownHostsFile={known_hosts_path}".format(known_hosts_path=_get_known_hosts_local_path()),
                      upload=False)

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def get_dumps(delete=False, *args, **kwargs):
    delete = fab_arg_to_bool(delete)

    with cd(env.deploy_path):
        print(Fore.BLUE + "Rsyncing local backups with remote")

        rsync_project(local_dir='data/',
                      remote_dir="{0}/data/backup".format(env.deploy_path.rstrip("/")),
                      exclude=['.git*', 'cache*', 'filer_*'],
                      delete=delete,
                      ssh_opts="-o UserKnownHostsFile={known_hosts_path}".format(known_hosts_path=_get_known_hosts_local_path()),
                      upload=False)

    print(Fore.GREEN + Style.BRIGHT + "Done.")


def _get_known_hosts_local_path():
    return os.path.normpath(os.path.expanduser(os.path.join(env.ssh_config_path, "../known_hosts")))


@task
def npm(upgrade=False, *args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Installing node_modules")

        # run("npm prune")
        run("npm set progress=false")
        run("npm install --no-optional")

        if upgrade:
            run("npm update --no-optional")

        run("npm set progress=true")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def yarn(upgrade=False, *args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Installing node_modules using yarn")
        run("yarn install")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='cl')
def clean(*args, **kwargs):
    with shell_env(**env.export_env):
        with cd(env.deploy_path):
            print(Fore.BLUE + "Cleaning Django project")

            if env.clear_cache:
                venv_run('python src/manage.py clearsessions')
                venv_run('python src/manage.py clear_cache')

            with settings(warn_only=True):
                venv_run('python src/manage.py thumbnail clear')

            venv_run('python src/manage.py clean_pyc --optimize --path=src/')
            venv_run('python src/manage.py compile_pyc --path=src/')

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='rs')
def rebuild_staticfiles(*args, **kwargs):
    if not confirm('Are you sure you want to rebuild all staticfiles?', default=False):
        abort('Rebuild cancelled')

    with cd(env.deploy_path):
        print(Fore.BLUE + "Rebuilding staticfiles")

        run("rm -rf data/static")

        venv_run('python src/manage.py collectstatic --noinput')
        run('bower install --config.interactive=false')

        gulp()

        venv_run('python src/manage.py compress')

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task()
def rebuild_virtualenv(*args, **kwargs):
    if not confirm('Are you sure you want to rebuild virtualenv? This will stop and start your app.', default=False):
        abort('Rebuild cancelled')

    with cd(env.deploy_path):
        stop()
        print(Fore.BLUE + "Rebuilding virtualenv")

        replace = env.venv_path.replace("/bin/activate", "")
        run("rm -rf {}".format(replace))

        run('virtualenv {}'.format(replace))
        update_python_tools()
        start()

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='g')
def gulp(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Starting gulp build")

        run("gulp clean")
        run("gulp build --production")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='cu')
def check_urls(*args, **kwargs):
    logging.basicConfig(level=logging.DEBUG)

    for url in env.urls_to_check:
        print("Checking `{0}`".format(url))
        r = requests.get(url, verify=env.urls_to_check_verify_ssl_certificate)
        if r.status_code != 200: abort("HTTP status for `{0}` is `{1}`.".format(url, r.status_code))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='upt')
def update_python_tools(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Updating Python tools")

        venv_run('easy_install --upgrade pip')
        venv_run('pip install --no-input --exists-action=i --use-wheel --upgrade setuptools wheel ipython ipdb')

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='c')
def check(*args, **kwargs):
    print(Fore.BLUE + "Checking local project")

    with settings(warn_only=True):
        local("git status --porcelain")

    local("python src/manage.py check --deploy")

    with settings(warn_only=True):
        local("python src/manage.py validate_templates")

    if env.pytest:
        local("pytest src/ --verbose --color=yes --showlocals")
    else:
        local("python src/manage.py test --noinput")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
def supervisorctl(command, *args, **kwargs):
    with cd(env.deploy_path):
        run('supervisorctl {command} {program_name}:*'.format(command=command, program_name=env.supervisor_program))


@task(alias='r')
def restart(*args, **kwargs):
    print(Fore.BLUE + "Restarting application group")

    supervisorctl("restart")
    status()

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task()
def stop(*args, **kwargs):
    print(Fore.BLUE + "Stopping application group")

    supervisorctl("stop")
    status()

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task()
def start(*args, **kwargs):
    print(Fore.BLUE + "Starting application group")

    supervisorctl("start")
    status()

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='gr')
def graceful_restart(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Restarting Gunicorn with HUP signal")
        run('supervisorctl pid {program_name}:{part}_gunicorn | xargs kill -s HUP'.format(program_name=env.supervisor_program, part=env.project_name))

        if env.celery_enabled:
            print(Fore.BLUE + "Restarting Celery with HUP signal")

            if env.celery_workers:
                for worker in env.celery_workers:
                    print(Fore.YELLOW + "Restarting worker `{}`".format(worker))
                    run('supervisorctl pid {program_name}:{part}_celeryd_{worker} | xargs kill -s HUP'.format(program_name=env.supervisor_program, part=env.project_name, worker=worker))
            else:
                print(Fore.YELLOW + "Restarting default worker")
                run('supervisorctl pid {program_name}:{part}_celeryd | xargs kill -s HUP'.format(program_name=env.supervisor_program, part=env.project_name))

            if env.celerybeat_enabled:
                run('supervisorctl pid {program_name}:{part}_celerybeat | xargs kill -s HUP'.format(program_name=env.supervisor_program, part=env.project_name))

        if env.huey_enabled:
            run('supervisorctl restart {program_name}:{part}_huey'.format(program_name=env.supervisor_program, part=env.project_name))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task()
def kill(*args, **kwargs):
    with cd(env.deploy_path):
        with settings(warn_only=True):
            print(Fore.BLUE + "Killing Gunicorn")
            run('supervisorctl pid {program_name}:{part}_gunicorn | xargs kill -9'.format(program_name=env.supervisor_program, part=env.project_name))

            if env.celery_enabled:
                print(Fore.BLUE + "Killing Celery")

                if env.celery_workers:
                    for worker in env.celery_workers:
                        print(Fore.YELLOW + "Killing worker `{}`".format(worker))

                        run('supervisorctl pid {program_name}:{part}_celeryd_{worker} | xargs kill -9'.format(program_name=env.supervisor_program, part=env.project_name, worker=worker))
                else:
                    print(Fore.YELLOW + "Killing default worker")
                    run('supervisorctl pid {program_name}:{part}_celerybeat | xargs kill -9'.format(program_name=env.supervisor_program, part=env.project_name))

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task()
def kill_celery(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Killing Celery")
        run("ps auxww | grep 'celery worker' | awk '{print $2}' | xargs kill -9")

    print(Fore.GREEN + Style.BRIGHT + "Done.")


@task(alias='s')
def status(*args, **kwargs):
    with cd(env.deploy_path):
        print(Fore.BLUE + "Retrieving status")

        run("supervisorctl status | grep \"{program_name}\"".format(program_name=env.supervisor_program))

        watched_services = [
            'nginx',
            'supervisor'
        ]

        if env.db_engine == 'postgresql':
            watched_services.append('postgresql')
        elif env.db_engine == 'mysql':
            watched_services.append('mysql')
        else:
            print("Unsupported database engine {}".format(env.db_engine))

        for service in watched_services:
            run('service {} status'.format(service), pty=False)

        if env.celery_enabled:
            with settings(warn_only=True):
                venv_run("celery --workdir=src/ --app=main status")

        print(Fore.GREEN + Style.BRIGHT + "Done.")


@task
@runs_once
def register_deployment(git_path="."):
    with(lcd(git_path)):
        revision = local('git log -n 1 --pretty="format:%H"', capture=True)
        branch = local('git rev-parse --abbrev-ref HEAD', capture=True)
        local('curl https://intake.opbeat.com/api/v1/organizations/{opbeat_organization_id}/apps/{opbeat_app_id}/releases/'
              ' -H "Authorization: Bearer {opbeat_authorization_bearer}"'
              ' -d rev="{rev}"'
              ' -d branch="{branch}"'
              ' -d status=completed'.format(opbeat_organization_id=env.opbeat_organization_id,
                                            opbeat_app_id=env.opbeat_app_id,
                                            opbeat_authorization_bearer=env.opbeat_authorization_bearer,
                                            rev=revision,
                                            branch=branch))
