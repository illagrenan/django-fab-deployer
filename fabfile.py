# coding=utf-8

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from fabric.context_managers import settings

from fabric.contrib.console import confirm
from fabric.decorators import task
from fabric.operations import local


@task()
def test_install():
    with settings(warn_only=True):
        local("pip uninstall fab_django_deploy --yes")
        print("Uninstall OK.")

    local("pip install --use-wheel --no-index --find-links dist fab_django_deploy")
    local("pip uninstall fab_django_deploy --yes")

    print("Install OK.")


@task()
def test():
    local("nosetests --with-coverage --cover-package=fab_django_deploy --cover-tests --cover-erase --with-doctest")

    print("Test OK.")


@task()
def build():
    local("pandoc --from=markdown --to=rst README.md -o _generated/README.rst")
    local("python setup.py sdist")
    local("python setup.py bdist_wheel")

    print("Build OK.")


@task()
def publish():
    if confirm(u'Really publish?', default=False):
        local('python setup.py sdist upload -r pypi')
        local('python setup.py bdist_wheel upload -r pypi')

        print("Published.")
