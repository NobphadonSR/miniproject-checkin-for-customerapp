#!/usr/bin/env bash
set -o errexit

# upgrade pip
python -m pip install --upgrade pip

# install requirements
pip install -r requirements.txt

# create static directory
mkdir -p staticfiles

# reset database and create new schema
python << END
import psycopg2
from urllib.parse import urlparse
import os

# Parse database URL
db_url = urlparse(os.environ.get('DATABASE_URL'))
conn = psycopg2.connect(
    dbname=db_url.path[1:],
    user=db_url.username,
    password=db_url.password,
    host=db_url.hostname,
    port=db_url.port
)
conn.autocommit = True
cur = conn.cursor()

# Drop and recreate schema
cur.execute('DROP SCHEMA public CASCADE;')
cur.execute('CREATE SCHEMA public;')
cur.execute('GRANT ALL ON SCHEMA public TO postgres;')
cur.execute('GRANT ALL ON SCHEMA public TO public;')

cur.close()
conn.close()
END

# run migrations
python manage.py makemigrations attendance
python manage.py migrate

# create superuser if needed
python << END
import os
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        'admin',
        'admin@example.com',
        os.environ.get('ADMIN_PASSWORD', 'adminpassword'),
        role='manager',
        department='it'
    )
END

# collect static
python manage.py collectstatic --no-input --clear