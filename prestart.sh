#!/bin/bash
set -e

# Create necessary directories
mkdir -p clips
mkdir -p uploads
mkdir -p transcriptions

# Print environment information
echo "Python version:"
python --version

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  echo "WARNING: DATABASE_URL is not set"
fi

# Check if SESSION_SECRET is set
if [ -z "$SESSION_SECRET" ]; then
  echo "WARNING: SESSION_SECRET is not set"
fi

# Run any pending database migrations
python -c "from app import app, db; app.app_context().push(); db.create_all()"

echo "Prestart tasks completed"
