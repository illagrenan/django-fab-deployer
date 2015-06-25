# coding=utf-8

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import shutil

from future import standard_library

standard_library.install_aliases()
from builtins import *

import six
import sys

if not six.PY2:
    print("Run Fabfile only under Python 2.x")
    sys.exit(0)

from fabric.context_managers import settings
from fabric.contrib.console import confirm
from fabric.decorators import task
from fabric.operations import local

try:
    from color_printer.colors import green, red
except ImportError:
    green = red = print


@task()
def update_package_tools():
    local("easy_install -U pip")
    local("pip install setuptools --upgrade")
    local("pip install wheel --upgrade")

    green("Updated.")


@task()
def install_requirements():
    local("pip install -r requirements.txt --upgrade --use-wheel")

    green("Installed || Updated.")


@task()
def clean():
    try:
        shutil.rmtree('django_fab_deployer.egg-info')
        shutil.rmtree('build')
        shutil.rmtree('dist')
        shutil.rmtree('__pycache__')
    except WindowsError as e:
        red(e.message)

    green("Cleaned")


@task()
def test_install():
    with settings(warn_only=True):
        local("pip uninstall django_fab_deployer --yes")
        green("Uninstall OK.")

    local("pip install --use-wheel --no-index --find-links dist django_fab_deployer")
    local("pip uninstall django_fab_deployer --yes")

    green("Install test OK.")


@task()
def test():
    local("nosetests --with-coverage --cover-package=django_fab_deployer --cover-tests --cover-erase --with-doctest")

    green("Test OK.")


@task()
def build():
    # pip install docutils
    local("python setup.py check --verbose --strict --restructuredtext")

    local("python setup.py build")
    local("python setup.py sdist")
    local("python setup.py bdist_wheel")
    # local("python setup.py bdist_wininst")

    green("Build OK.")


@task()
def publish():
    if confirm(u'Really publish?', default=False):
        local('python setup.py sdist upload -r pypi')
        local('python setup.py bdist_wheel upload -r pypi')

        green("Published.")
