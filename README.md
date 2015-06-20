# Django FAB Deployer #

[![Requirements Status](https://requires.io/github/illagrenan/django-fab-deployer/requirements.svg?branch=master)](https://requires.io/github/illagrenan/django-fab-deployer/requirements/?branch=master)

## Installation ##

```bash
pip install --upgrade django_fab_deployer
```

## Usage ##

```bash
# Generate example deployment configuration:
djdeploy write_example_config
```

Command above will generate `example.json` file in current directory. Example of deployment configuration:

```json
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
```

Save this file as `deploy.json` and run:

```bash
djdeploy dev deploy
# Or
djdeploy production deploy
```