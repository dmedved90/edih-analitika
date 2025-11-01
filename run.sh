#!/bin/bash

# EDIH Analytics - Run Script
# Quick start script for Linux/Mac

set -e

echo "🚀 Starting EDIH Analytics Dashboard..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env - Please edit it with your API keys"
        exit 1
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Run configuration test
echo "🧪 Testing configuration..."
python test_config.py
if [ $? -ne 0 ]; then
    echo "❌ Configuration test failed. Please fix issues before running."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Run the application
echo "✅ Starting application on http://localhost:8501"
echo "Press Ctrl+C to stop"
streamlit run app.py

deactivate
