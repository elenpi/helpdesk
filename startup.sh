#!/bin/bash
export PATH="$PWD/git:${PATH}"
python manage.py collectstatic && gunicorn --workers 2 myproject.wsgi
