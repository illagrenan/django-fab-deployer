Fab Django deploy
=================

|Requirements Status|

Installation
------------

**This package is not yet on PyPI.**

.. code:: bash

    pip install --upgrade git+git://github.com/illagrenan/fab-django-deploy.git#egg=fab-django-deploy

Usage
-----

.. code:: bash

    # Generate example deployment configuration:
    fdep write_example_config

Command above will generate ``example.json`` file in current directory.
Example of deployment configuration:

.. code:: json

    {
      "dev": {
        "celery_enabled": true, 
        "deploy_path": "/var/www/dev_my_project", 
        "hosts": "8.8.8.8", 
        "key_filename": "~/.ssh/id_rsa.PUB", 
        "project_name": "dev_my_project", 
        "user": "dev_my_project", 
        "venv_path": "data/.venv/bin/activate", 
        "warn_on_deploy": false
      }, 
      "production": {
        "celery_enabled": true, 
        "deploy_path": "/var/www/prod_my_project", 
        "hosts": "8.8.8.8", 
        "key_filename": "~/.ssh/id_rsa.PUB", 
        "project_name": "prod_my_project", 
        "user": "prod_my_project", 
        "venv_path": "data/.venv/bin/activate", 
        "warn_on_deploy": true
      }
    }

Save this file as ``deploy.json`` and run:

.. code:: bash

    fdep dev deploy
    # Or
    fdep production deploy

.. |Requirements Status| image:: https://requires.io/github/illagrenan/fab-django-deploy/requirements.svg?branch=master
   :target: https://requires.io/github/illagrenan/fab-django-deploy/requirements/?branch=master
