#!/bin/bash
# Startup script for Carpool Time Backend

echo "Starting Carpool Time Backend Service..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Start the service
echo "Starting Flask server on port 1338..."
python -m src.app
