#!/bin/bash

###############################################################################
# inDoc E2E Test Setup Script
# 
# This script prepares your environment for running comprehensive E2E tests
###############################################################################

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Setting up inDoc E2E Testing Environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm version: $(npm --version)"
echo ""

# Install root package dependencies (Playwright)
echo "📦 Installing E2E test dependencies..."
npm install
echo ""

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
npx playwright install --with-deps chromium
echo ""

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..
echo ""

# Check if conda environment exists
if conda env list | grep -q "indoc"; then
    echo "✅ Conda environment 'indoc' exists"
else
    echo "⚠️  Conda environment 'indoc' not found"
    echo "   Please create it with: conda create -n indoc python=3.11"
fi
echo ""

# Check if backend dependencies are installed
echo "🐍 Checking backend dependencies..."
if [ -f "requirements.txt" ]; then
    echo "   Run: conda run -n indoc pip install -r requirements.txt"
else
    echo "   requirements.txt not found"
fi
echo ""

# Check if database is accessible
echo "🗄️  Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    if psql -U postgres -c "SELECT 1" &> /dev/null; then
        echo "✅ PostgreSQL is accessible"
    else
        echo "⚠️  PostgreSQL is installed but not accessible"
        echo "   Make sure PostgreSQL is running"
    fi
else
    echo "⚠️  PostgreSQL command not found"
    echo "   Make sure PostgreSQL is installed and running"
fi
echo ""

# Check if Redis is running
echo "💾 Checking Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis is installed but not running"
        echo "   Start Redis with: redis-server"
    fi
else
    echo "⚠️  Redis command not found"
    echo "   Install Redis: brew install redis (macOS) or apt install redis (Linux)"
fi
echo ""

# Check optional services
echo "🔍 Checking optional services..."

# Elasticsearch
if curl -s http://localhost:9200 &> /dev/null; then
    echo "✅ Elasticsearch is running"
else
    echo "ℹ️  Elasticsearch not running (optional but recommended)"
fi

# Qdrant
if curl -s http://localhost:8080/v1/.well-known/ready &> /dev/null; then
    echo "✅ Qdrant is running"
else
    echo "ℹ️  Qdrant not running (optional but recommended)"
fi
echo ""

# Create test directories
echo "📁 Creating test directories..."
mkdir -p tmp/e2e-test-files
mkdir -p playwright-report
echo "✅ Test directories created"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ E2E Test Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Start the application:"
echo "   make local-e2e"
echo ""
echo "2. Run smoke test (quick validation):"
echo "   npm run test:smoke"
echo ""
echo "3. Run full production validation:"
echo "   npm run test:production"
echo ""
echo "4. View test UI (interactive mode):"
echo "   npm run test:e2e:ui"
echo ""
echo "📚 See tests/e2e/README.md for detailed documentation"
echo ""


