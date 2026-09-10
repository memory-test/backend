#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# We are using `gunicorn` for production, see:
# http://docs.gunicorn.org/en/stable/configure.html

# Check that $DJANGO_ENV is set to "production",
# fail otherwise, since it may break things:
echo "DJANGO_ENV is $DJANGO_ENV"
if [ "$DJANGO_ENV" != 'production' ]; then
  echo 'Error: DJANGO_ENV is not set to "production".'
  echo 'Application will not start.'
  exit 1
fi

export DJANGO_ENV

# Run python specific scripts:
# Running migrations in startup script might not be the best option, see:
# docs/pages/template/production-checklist.rst
python /code/backend/manage.py migrate --noinput
python /code/backend/manage.py collectstatic --noinput --clear
# python /code/backend/manage.py compilemessages

# create superuser with DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_EMAIL
python /code/backend/manage.py createsuperuser  --no-input  || true



# Start gunicorn:
# Docs: http://docs.gunicorn.org/en/stable/settings.html
# Make sure it is in sync with `django/ci.sh` check:
/usr/local/bin/gunicorn \
  --config python:docker.django.gunicorn_config backend.wsgi
