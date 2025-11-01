#!/bin/bash

# Initial GitHub Setup Script
# Prepares repository for first push to GitHub

set -e

echo "🚀 EDIH Analytics - GitHub Setup"
echo "================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed${NC}"
    echo "Please install Git first: https://git-scm.com/downloads"
    exit 1
fi

echo -e "${GREEN}✓ Git is installed${NC}"
echo ""

# Check if already a git repository
if [ -d .git ]; then
    echo -e "${YELLOW}⚠ This is already a Git repository${NC}"
    read -p "Do you want to reinitialize? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping git init"
    else
        rm -rf .git
        git init
        echo -e "${GREEN}✓ Reinitialized Git repository${NC}"
    fi
else
    git init
    echo -e "${GREEN}✓ Initialized Git repository${NC}"
fi

echo ""
echo "🔒 Running security check..."
chmod +x security_check.sh
./security_check.sh

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Security check failed!${NC}"
    echo "Please fix the issues before continuing"
    exit 1
fi

echo ""
echo "📝 Preparing initial commit..."

# Make scripts executable
chmod +x deploy.sh
chmod +x security_check.sh

# Add all files
git add .

# Show what will be committed
echo ""
echo "Files to be committed:"
git status --short

echo ""
read -p "Do you want to proceed with the commit? (Y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Commit cancelled"
    exit 0
fi

# Create initial commit
git commit -m "🎉 Initial commit - EDIH Analytics v5.0 Production Ready

- Refactored for production deployment
- Added security improvements (environment variables)
- Implemented logging system
- Modular architecture
- Docker support
- Comprehensive documentation

See CHANGELOG.md for details"

echo ""
echo -e "${GREEN}✓ Initial commit created${NC}"

# Check for remote
if git remote -v | grep -q "origin"; then
    echo ""
    echo -e "${YELLOW}⚠ Remote 'origin' already exists${NC}"
    git remote -v
    echo ""
    read -p "Do you want to update it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter new GitHub repository URL: " REPO_URL
        git remote set-url origin "$REPO_URL"
        echo -e "${GREEN}✓ Remote URL updated${NC}"
    fi
else
    echo ""
    echo -e "${BLUE}📦 GitHub Repository Setup${NC}"
    echo ""
    echo "Steps to create a GitHub repository:"
    echo "1. Go to https://github.com/new"
    echo "2. Create a new repository (e.g., edih-analitika)"
    echo "3. Do NOT initialize with README, .gitignore, or license"
    echo ""
    read -p "Enter your GitHub repository URL: " REPO_URL
    
    if [ -z "$REPO_URL" ]; then
        echo -e "${YELLOW}⚠ No URL provided. You can add it later with:${NC}"
        echo "   git remote add origin <your-repo-url>"
    else
        git remote add origin "$REPO_URL"
        echo -e "${GREEN}✓ Remote 'origin' added${NC}"
    fi
fi

echo ""
echo "🌿 Checking branch name..."

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Current branch: $CURRENT_BRANCH"
    read -p "Rename to 'main'? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git branch -M main
        echo -e "${GREEN}✓ Branch renamed to 'main'${NC}"
    fi
fi

echo ""
echo "================================="
echo "🎉 Setup Complete!"
echo "================================="
echo ""
echo "Your repository is ready to push to GitHub!"
echo ""
echo "Next steps:"
echo ""
echo "1️⃣ If you haven't created a GitHub repository yet:"
echo "   • Go to https://github.com/new"
echo "   • Create a new repository"
echo "   • Copy the repository URL"
echo "   • Run: git remote add origin <your-repo-url>"
echo ""
echo "2️⃣ Push to GitHub:"
echo "   ${GREEN}git push -u origin main${NC}"
echo ""
echo "3️⃣ Configure GitHub repository settings:"
echo "   • Add repository description"
echo "   • Add topics: streamlit, analytics, edih, dashboard"
echo "   • Configure branch protection rules"
echo ""
echo "4️⃣ Add secrets for GitHub Actions (if using):"
echo "   • Go to Settings > Secrets and variables > Actions"
echo "   • Add: OPENAI_API_KEY, DEEPSEEK_API_KEY (optional)"
echo ""
echo "5️⃣ Share with team:"
echo "   • Provide .env.example"
echo "   • Share README.md and DEPLOYMENT.md"
echo ""
echo "📚 Documentation:"
echo "   • README.md - User guide"
echo "   • DEPLOYMENT.md - Deployment instructions"
echo "   • CHANGELOG.md - Version history"
echo ""
echo "🔒 Security reminders:"
echo "   • NEVER commit .env file"
echo "   • Rotate API keys regularly"
echo "   • Review commits before pushing"
echo "   • Use branch protection in production"
echo ""
echo "Commands:"
echo "   • View status:  git status"
echo "   • View remote:  git remote -v"
echo "   • View commits: git log --oneline"
echo "   • Push code:    git push -u origin main"
echo ""

# Offer to push now
if git remote -v | grep -q "origin"; then
    echo ""
    read -p "Do you want to push to GitHub now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Pushing to GitHub..."
        git push -u origin main
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}🎉 Successfully pushed to GitHub!${NC}"
            echo ""
            echo "Your repository is now available online!"
            echo ""
        else
            echo ""
            echo -e "${RED}❌ Push failed${NC}"
            echo "This might be because:"
            echo "  • Remote repository doesn't exist"
            echo "  • Authentication failed"
            echo "  • Network issues"
            echo ""
            echo "Try:"
            echo "  1. Verify remote URL: git remote -v"
            echo "  2. Check GitHub credentials"
            echo "  3. Push manually: git push -u origin main"
        fi
    fi
fi

echo ""
echo "Happy coding! 🚀"
echo ""
