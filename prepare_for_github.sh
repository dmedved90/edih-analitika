#!/bin/bash

# EDIH Analytics - GitHub Preparation Script
# This script prepares the project for GitHub upload

set -e

echo "📦 Preparing EDIH Analytics for GitHub..."
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "EDIH-Analitika.py" ]; then
    echo "❌ Error: EDIH-Analitika.py not found. Please run this script from the project root."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p .github/workflows

# Check for .env file
if [ -f ".env" ]; then
    echo "⚠️  WARNING: .env file exists!"
    echo "   This file should NOT be committed to GitHub."
    read -p "   Move it to .env.local? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mv .env .env.local
        echo "✅ Moved .env to .env.local"
    fi
fi

# Ensure .env.example exists
if [ ! -f ".env.example" ]; then
    echo "❌ Error: .env.example not found!"
    echo "   Creating template..."
    cat > .env.example << 'EOF'
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Application Settings
APP_FOLDER_WINDOWS=G:\Moj disk\EDIH
APP_FOLDER_LINUX=/home/damirmint/EDIH

# Performance Settings
CACHE_TTL=3600
MAX_UPLOAD_SIZE=200

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/edih_app.log
EOF
    echo "✅ Created .env.example"
fi

# Check .gitignore
if [ ! -f ".gitignore" ]; then
    echo "❌ Error: .gitignore not found!"
    exit 1
fi

# Verify critical files exist
echo "🔍 Verifying files..."
REQUIRED_FILES=(
    "EDIH-Analitika.py"
    "requirements.txt"
    ".gitignore"
    ".env.example"
    "README.md"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo "❌ Missing required files:"
    printf '   - %s\n' "${MISSING_FILES[@]}"
    exit 1
fi

# Check for sensitive data in files
echo "🔒 Checking for sensitive data..."
if grep -r "sk-proj-\|sk-[0-9a-zA-Z]\{48\}" --include="*.py" --exclude-dir=venv . > /dev/null 2>&1; then
    echo "⚠️  WARNING: Possible API keys found in code!"
    echo "   Please review and remove them before pushing."
    grep -rn "sk-proj-\|sk-[0-9a-zA-Z]\{48\}" --include="*.py" --exclude-dir=venv .
    exit 1
fi

# Initialize git if not already
if [ ! -d ".git" ]; then
    echo "🔧 Initializing git repository..."
    git init
    echo "✅ Git initialized"
fi

# Create GitHub Actions workflow
echo "⚙️  Creating GitHub Actions workflow..."
cat > .github/workflows/test.yml << 'EOF'
name: Test

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install system dependencies
      run: |
        sudo apt-get update
            
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Test configuration
      run: |
        python test_config.py || true
EOF

# Summary
echo ""
echo "=========================================="
echo "✅ Project prepared for GitHub!"
echo ""
echo "📋 Next steps:"
echo "   1. Review all files"
echo "   2. Add files to git:"
echo "      git add ."
echo "   3. Commit:"
echo "      git commit -m 'Initial commit - Production ready v5.0'"
echo "   4. Add remote:"
echo "      git remote add origin <your-repo-url>"
echo "   5. Push:"
echo "      git push -u origin main"
echo ""
echo "⚠️  Remember:"
echo "   - NEVER commit .env file"
echo "   - Review sensitive data"
echo "   - Update README with your repo URL"
echo "=========================================="
