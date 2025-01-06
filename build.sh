#!/usr/bin/env bash
# exit on error
set -o errexit

# upgrade pip
python -m pip install --upgrade pip

# install requirements
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate