#!/bin/bash

# Security Check Script for EDIH Analytics Dashboard
# Run this before pushing to GitHub

set -e

echo "🔒 EDIH Analytics - Security Check"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

# Function to report errors
error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    ERRORS=$((ERRORS + 1))
}

# Function to report warnings
warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

# Function to report success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

echo "1️⃣ Checking for hardcoded API keys..."
if grep -r "sk-proj" . --exclude-dir=venv --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null; then
    error "Found hardcoded OpenAI API key"
else
    success "No OpenAI API keys found in code"
fi

if grep -r "sk-[0-9a-f]" . --exclude-dir=venv --exclude-dir=.git --exclude-dir=node_modules --exclude="*.md" 2>/dev/null; then
    error "Found potential hardcoded API keys"
else
    success "No suspicious API key patterns found"
fi

echo ""
echo "2️⃣ Checking for exposed credentials..."
if grep -rE "(password|passwd|pwd|secret).*=.*['\"]" . --exclude-dir=venv --exclude-dir=.git --exclude="*.md" --exclude="security_check.sh" 2>/dev/null | grep -v "example\|template\|TODO\|config"; then
    error "Found potential exposed credentials"
else
    success "No exposed credentials found"
fi

echo ""
echo "3️⃣ Checking .env file..."
if [ -f .env ]; then
    warning ".env file exists - make sure it's in .gitignore"
else
    success ".env file not present (good for GitHub)"
fi

echo ""
echo "4️⃣ Checking .gitignore..."
if [ -f .gitignore ]; then
    if grep -q "\.env" .gitignore; then
        success ".env is in .gitignore"
    else
        error ".env is NOT in .gitignore"
    fi
    
    if grep -q "\.log" .gitignore; then
        success "Log files are in .gitignore"
    else
        warning "Log files might not be ignored"
    fi
else
    error ".gitignore file not found"
fi

echo ""
echo "5️⃣ Checking for .env.example..."
if [ -f .env.example ]; then
    success ".env.example exists"
    
    # Check if it contains placeholder values
    if grep -q "your_.*_key_here\|sk-proj\|sk-[0-9]" .env.example; then
        warning ".env.example may contain real API keys - should only have placeholders"
    else
        success ".env.example looks good"
    fi
else
    error ".env.example not found"
fi

echo ""
echo "6️⃣ Checking for large data files..."
if find . -type f -size +10M -not -path "./venv/*" -not -path "./.git/*" 2>/dev/null | grep -v "\.git"; then
    warning "Large files found - consider using Git LFS or excluding from repo"
else
    success "No large files found"
fi

echo ""
echo "7️⃣ Checking for common sensitive patterns..."

# Database connection strings
if grep -rE "(mysql|postgresql|mongodb)://[^/]+:[^@]+@" . --exclude-dir=venv --exclude-dir=.git 2>/dev/null; then
    error "Found database connection strings with credentials"
else
    success "No database connection strings found"
fi

# AWS keys
if grep -rE "AKIA[0-9A-Z]{16}" . --exclude-dir=venv --exclude-dir=.git 2>/dev/null; then
    error "Found potential AWS access keys"
else
    success "No AWS keys found"
fi

echo ""
echo "8️⃣ Checking file permissions..."
if [ -f .env ]; then
    PERMS=$(stat -c %a .env 2>/dev/null || stat -f %A .env 2>/dev/null)
    if [ "$PERMS" -le 600 ]; then
        success ".env has secure permissions ($PERMS)"
    else
        warning ".env has loose permissions ($PERMS) - recommend 600"
    fi
fi

echo ""
echo "9️⃣ Checking for TODO and FIXME..."
TODO_COUNT=$(grep -r "TODO\|FIXME" . --exclude-dir=venv --exclude-dir=.git --exclude="security_check.sh" 2>/dev/null | wc -l)
if [ "$TODO_COUNT" -gt 0 ]; then
    warning "Found $TODO_COUNT TODO/FIXME comments"
else
    success "No TODO/FIXME comments found"
fi

echo ""
echo "🔟 Checking Python imports..."
if grep -r "import os" . --include="*.py" --exclude-dir=venv 2>/dev/null | grep -v "config.py\|logger.py"; then
    warning "Direct os imports found - consider using pathlib"
fi

echo ""
echo "================================"
echo "📊 Security Check Summary"
echo "================================"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ ERRORS: $ERRORS${NC}"
    echo ""
    echo "🚫 DO NOT push to GitHub until errors are fixed!"
    echo ""
    echo "Common fixes:"
    echo "  1. Remove hardcoded API keys"
    echo "  2. Add .env to .gitignore"
    echo "  3. Use environment variables"
    echo "  4. Create .env.example with placeholders"
    exit 1
else
    echo -e "${GREEN}✓ No critical errors found${NC}"
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠ WARNINGS: $WARNINGS${NC}"
    echo ""
    echo "Review warnings before pushing"
fi

echo ""
echo "✅ Security check complete!"
echo ""
echo "Next steps:"
echo "  1. Review any warnings above"
echo "  2. Commit your changes: git add . && git commit -m 'Initial commit'"
echo "  3. Push to GitHub: git push origin main"
echo ""
echo "🔒 Remember:"
echo "  • Never commit .env files"
echo "  • Use environment variables for secrets"
echo "  • Keep .env.example updated with placeholders"
echo "  • Rotate API keys regularly"
echo ""
