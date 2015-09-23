# coding=utf-8

from setuptools import setup

try:
    from pypandoc import convert

    def read_md(file_name):
        # http://stackoverflow.com/a/23265673/752142
        return convert(file_name, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")

    def read_md(file_name):
        try:
            return open(file_name, 'r').read()
        except UnicodeDecodeError:
            return "Encoding problems with README.md"

# https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
setup(
    name='django_fab_deployer',
    version='0.0.12',
    description='TODO Add description',
    long_description=read_md('README.md'),
    url='https://github.com/illagrenan/django-fab-deployer',
    license='MIT',
    author='Vašek Dohnal',
    author_email='vaclav.dohnal@gmail.com',

    # The exclude makes sure that a top-level tests package doesn’t get
    # installed (it’s still part of the source distribution)
    # since that would wreak havoc.
    # find_packages(exclude=['tests*'])
    packages=['django_fab_deployer'],

    install_requires=['fabric', 'color-printer', 'paramiko==1.15.1', 'terminaltables'],
    dependency_links=[
        'git+git://github.com/illagrenan/color-printer.git#egg=color-printer',
    ],
    entry_points={
        'console_scripts': [
            'djdeploy=django_fab_deployer.runner:main'
        ],
    },
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Environment :: Console',
        'Intended Audience :: Developers'
    ],
)
