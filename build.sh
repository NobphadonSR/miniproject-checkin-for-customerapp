#!/usr/bin/env bash
# exit on error
set -o errexit

# upgrade pip
python -m pip install --upgrade pip

# install requirements
pip install -r requirements.txt

# create static directory if it doesn't exist
mkdir -p staticfiles

# collect static files
python manage.py collectstatic --no-input --clear

# run migrations
python manage.py migrate --no-input