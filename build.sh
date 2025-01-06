#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# รันเฉพาะครั้งแรกที่ deploy หรือเมื่อมีการเปลี่ยนแปลง model
python manage.py makemigrations
python manage.py migrate

python manage.py collectstatic --no-input