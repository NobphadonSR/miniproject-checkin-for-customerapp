#!/usr/bin/env bash
set -o errexit

echo "🚀 Building application..."

# upgrade pip
python -m pip install --upgrade pip

# install requirements
pip install -r requirements.txt

echo "📦 Creating static directory..."
mkdir -p staticfiles

echo "🗄️ Resetting database..."
python << END
import psycopg2
from urllib.parse import urlparse
import os

try:
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

    print("Database reset successful")
except Exception as e:
    print(f"Error resetting database: {str(e)}")
finally:
    try:
        cur.close()
        conn.close()
    except:
        pass
END

echo "🔄 Running migrations..."
python manage.py makemigrations attendance --noinput
python manage.py migrate --noinput

echo "🌱 Loading initial data..."
python manage.py initial_data

echo "📚 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build completed successfully!"