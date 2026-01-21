#!/bin/sh
# Developer note:
# - Database lives in the 'db' container.
# - Migrations are run automatically on container start.
# - To run Django commands manually, use:
#       docker compose exec web python manage.py <command>
#   rather than calling manage.py directly on the host.
# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! pg_isready -h $DB_HOST -U $DB_USER; do
  sleep 2
done

# Create the database if it doesn't exist
echo "Checking if database exists..."
python manage.py shell -c "
from django.conf import settings
import psycopg2
from psycopg2 import sql

try:
    conn = psycopg2.connect(
        dbname='postgres',
        user='$DB_USER',
        password='$DB_PASSWORD',
        host='$DB_HOST'
    )
    conn.autocommit = True
    cursor = conn.cursor()

    dbname = settings.DATABASES['default']['NAME']

    cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (dbname,))
    exists = cursor.fetchone()

    if not exists:
        create_db = sql.SQL('CREATE DATABASE {} WITH ENCODING %s TEMPLATE template0;').format(
            sql.Identifier(dbname)
        )
        cursor.execute(create_db, ('UTF8',))
        print('Database created')
    else:
        print('Database already exists')

    cursor.close()
    conn.close()
except Exception as e:
    print('Database error:', str(e))
"


# Enable vector extension
echo "Enabling vector extension..."
python manage.py dbshell << EOF
CREATE EXTENSION IF NOT EXISTS vector;
\q
EOF

# Create missing migrations
echo "Creating migrations..."
python manage.py makemigrations --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    print('Superuser created')
else:
    print('Superuser already exists')
"

echo "Starting Django server..."
exec "$@"