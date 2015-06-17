# coding=utf-8

from setuptools import setup

# https://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
setup(
    name='fab_django_deploy',
    version='0.0.1',
    description='TODO Add description',

    # ########################################################################
    #
    # README.rst is generated from README.md:
    #
    # $ pandoc --from=markdown --to=rst README.md -o .tmp/README.rst
    #
    # ~ OR ~
    #
    # $ fab build
    # ########################################################################
    long_description=(open('_generated/README.rst').read()),

    url='https://github.com/illagrenan/fab-django-deploy',
    license='MIT',
    author='Vašek Dohnal',
    author_email='vaclav.dohnal@gmail.com',

    # The exclude makes sure that a top-level tests package doesn’t get
    # installed (it’s still part of the source distribution)
    # since that would wreak havoc.
    # find_packages(exclude=['tests*'])
    packages=['fab_django_deploy'],


    install_requires=['fabric', 'color_printer', 'paramiko==1.15.1'],
    dependency_links=[
        'git+git://github.com/illagrenan/fab-django-deploy.git#egg=fab-django-deploy',
    ],
    entry_points={
        'console_scripts': [
            'fdep=fab_django_deploy.runner:main'
        ],
    },
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Environment :: Console',
        'Intended Audience :: Developers'
    ],
)
