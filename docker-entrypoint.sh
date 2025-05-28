#!/bin/bash

# Docker entrypoint script for EPV application
# This script handles initialization and startup

set -e

echo "Starting EPV Application..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z db 3306; do
    echo "Waiting for MySQL database connection..."
    sleep 2
done
echo "Database is ready!"

# Initialize database if needed
echo "Initializing database..."
python -c "
from app import app, db, init_db
with app.app_context():
    try:
        # Test database connection
        db.engine.execute('SELECT 1')
        print('Database connection successful')
        
        # Initialize database
        init_db(app)
        print('Database initialization completed')
    except Exception as e:
        print(f'Database initialization error: {e}')
        exit(1)
"

# Create necessary directories
mkdir -p /app/logs
mkdir -p /app/uploads
mkdir -p /app/temp

# Set proper permissions
chmod 755 /app/logs
chmod 755 /app/uploads
chmod 755 /app/temp

echo "Starting application server..."

# Start the application based on environment
if [ "$FLASK_ENV" = "production" ]; then
    echo "Starting production server with Gunicorn..."
    exec gunicorn --config gunicorn.conf.py app:app
else
    echo "Starting development server..."
    exec python app.py
fi
