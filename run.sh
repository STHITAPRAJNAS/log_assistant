#!/bin/bash

# LogDetective Startup Script
# This script sets up and runs the LogDetective application

set -e

echo "🔍 Starting LogDetective - Splunk Assistant"
echo "=========================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📋 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Please create a .env file with your configuration."
    echo "   See README.md for details."
    echo ""
    echo "   Example .env content:"
    echo "   SPLUNK_HOST=your-splunk-host.com"
    echo "   SPLUNK_USERNAME=your-username"
    echo "   SPLUNK_PASSWORD=your-password"
    echo "   AWS_ACCESS_KEY_ID=your-aws-key"
    echo "   AWS_SECRET_ACCESS_KEY=your-aws-secret"
    echo ""
    read -p "   Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ Found .env configuration file"
fi

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo ""
echo "🚀 Starting LogDetective application..."
echo "   Navigate to: http://localhost:8501"
echo "   Press Ctrl+C to stop the application"
echo ""

# Run the Streamlit application
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 