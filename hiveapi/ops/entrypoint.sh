#!/bin/bash
# Entrypoint script for DayZ HiveAPI
# Waits for database, runs migrations, seeds if requested, and starts the application

# Exit immediately if a command exits with a non-zero status
# Treat unset variables as an error
# Exit if any command in a pipeline fails
set -euo pipefail

echo "Starting DayZ HiveAPI entrypoint script..."

# Default AUTO_SEED to true if not set
AUTO_SEED=${AUTO_SEED:-true}

# Extract host and port from DB_URL
# This handles both postgres:// and postgresql:// URL formats
python3 -c "
import sys
import time
import socket
import re
import os

db_url = os.environ.get('DB_URL', '')
if not db_url:
    print('DB_URL environment variable not set')
    sys.exit(1)

# Extract host and port using regex
match = re.search(r'(?:postgres|postgresql)://[^:]+:[^@]+@([^:]+):(\d+)', db_url)
if not match:
    print(f'Could not parse host and port from DB_URL: {db_url}')
    sys.exit(1)

host, port = match.groups()
port = int(port)

print(f'Waiting for database at {host}:{port} to be available...')

# Try to connect to the database
max_retries = 30
retry_interval = 2
for i in range(max_retries):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((host, port))
        sock.close()
        print(f'Successfully connected to database at {host}:{port}')
        sys.exit(0)
    except Exception as e:
        if i < max_retries - 1:
            print(f'Attempt {i+1}/{max_retries}: Database not available yet. Retrying in {retry_interval} seconds...')
            time.sleep(retry_interval)
        else:
            print(f'Could not connect to database after {max_retries} attempts: {str(e)}')
            sys.exit(1)
"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Seed the database if AUTO_SEED is true
if [ "$AUTO_SEED" = "true" ]; then
    echo "Seeding the database..."
    python -m scripts.seed || echo "Warning: Database seeding failed, but continuing startup"
else
    echo "Skipping database seeding (AUTO_SEED=$AUTO_SEED)"
fi

# Start the application
echo "Starting the application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
