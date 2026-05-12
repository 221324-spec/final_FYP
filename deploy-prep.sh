#!/bin/bash
# Deployment Preparation Script
# Run this BEFORE deploying to validate your setup

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  Recovery Road - Deployment Prep Check"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_mark="${GREEN}✓${NC}"
cross_mark="${RED}✗${NC}"

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${check_mark} Found: $1"
        return 0
    else
        echo -e "${cross_mark} Missing: $1"
        return 1
    fi
}

# Function to check command exists
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${check_mark} Installed: $1"
        return 0
    else
        echo -e "${cross_mark} Not installed: $1"
        return 1
    fi
}

echo "📁 Project Structure Check:"
echo "─────────────────────────────────────────────────────────────"
check_file "backend/server.js"
check_file "backend/package.json"
check_file "backend/ml_service/app.py"
check_file "backend/ml_service/requirements.txt"
check_file "frontend/package.json"
check_file "frontend/vite.config.js"
check_file "backend/.env"

echo ""
echo "📦 Installed Tools:"
echo "─────────────────────────────────────────────────────────────"
check_command "node"
check_command "npm"
check_command "python"
check_command "git"

echo ""
echo "🔐 Environment Variables:"
echo "─────────────────────────────────────────────────────────────"

# Source .env file
if [ -f "backend/.env" ]; then
    export $(cat backend/.env | xargs)
    
    # Check critical variables
    if [ -n "$GROQ_API_KEY" ]; then
        echo -e "${check_mark} GROQ_API_KEY is set"
    else
        echo -e "${cross_mark} GROQ_API_KEY is NOT set"
    fi
    
    if [ -n "$MONGO_URI" ]; then
        echo -e "${check_mark} MONGO_URI is set"
    else
        echo -e "${YELLOW}⚠${NC} MONGO_URI not set (will be needed for production)"
    fi
    
    if [ -n "$JWT_SECRET" ]; then
        echo -e "${check_mark} JWT_SECRET is set"
    else
        echo -e "${cross_mark} JWT_SECRET is NOT set"
    fi
else
    echo -e "${RED}✗ backend/.env not found${NC}"
fi

echo ""
echo "📝 Production Checklist:"
echo "─────────────────────────────────────────────────────────────"
echo -e "${YELLOW}⚠${NC} For production deployment, ensure:"
echo "  - [ ] MongoDB Atlas cluster created"
echo "  - [ ] MONGO_URI updated in backend/.env"
echo "  - [ ] JWT_SECRET set to random 32+ character string"
echo "  - [ ] GitHub repository is public or connected to Vercel/Railway"
echo "  - [ ] Groq API key is valid (test with: npm run test-groq)"
echo "  - [ ] All environment variables documented in DEPLOYMENT_QUICK_START.md"

echo ""
echo "✅ Pre-deployment check complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Update MONGO_URI in backend/.env if needed"
echo "2. Generate new JWT_SECRET: openssl rand -hex 32"
echo "3. Commit changes: git add . && git commit -m 'Production config'"
echo "4. Follow DEPLOYMENT_QUICK_START.md for hosting"
echo ""
