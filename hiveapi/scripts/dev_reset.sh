#!/bin/bash
# dev_reset.sh - Reset the hive database to a clean state
# Usage: ./scripts/dev_reset.sh

set -e  # Exit immediately if a command exits with a non-zero status

echo "Resetting hive database..."

# Drop and recreate the database
echo "Dropping and recreating database..."
docker-compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS hive;"
docker-compose exec -T db psql -U postgres -c "CREATE DATABASE hive WITH OWNER postgres;"

# Enable pgcrypto extension
echo "Enabling pgcrypto extension..."
docker-compose exec -T db psql -U postgres -d hive -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# Run migrations if alembic is set up
if [ -f "alembic.ini" ]; then
    echo "Running migrations..."
    docker-compose exec api alembic upgrade head
fi

echo "Database reset complete!"
echo "You may want to run the seed script: python -m scripts.seed"

# Make this script executable when created:
# chmod +x scripts/dev_reset.sh
