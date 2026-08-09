#!/bin/bash

# inDoc SaaS Platform Startup Script
# This script starts the full SaaS platform with all enhanced features

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting inDoc SaaS Platform${NC}"
echo "======================================"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Check Docker Compose
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker Compose is not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose is available${NC}"

# Create .env if needed
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please update .env with your configuration${NC}"
    echo -e "${YELLOW}   Especially update POSTGRES_PASSWORD and JWT_SECRET_KEY${NC}"
fi

# Check for existing PostgreSQL on localhost:5432
echo -e "${BLUE}🐘 Checking existing PostgreSQL...${NC}"
if lsof -i :5432 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is running on localhost:5432${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not running on localhost:5432${NC}"
    echo -e "${YELLOW}   Please start your PostgreSQL instance first${NC}"
    exit 1
fi

# Check for Ollama (required - using existing instance)
echo -e "${BLUE}🤖 Checking Ollama...${NC}"
if pgrep -f "ollama" > /dev/null; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
    
    # Check for available models
    if ollama list 2>/dev/null | grep -q "gpt-oss:120b\|llama2\|mistral"; then
        echo -e "${GREEN}✅ LLM models available${NC}"
    else
        echo -e "${YELLOW}📥 No LLM models found. You can pull one with:${NC}"
        echo "   ollama pull llama2"
    fi
else
    echo -e "${YELLOW}⚠️  Ollama not installed. LLM features will be limited.${NC}"
    echo "   Install with: curl -fsSL https://ollama.com/install.sh | sh"
fi

echo ""
echo -e "${BLUE}🐳 Starting Docker services...${NC}"

# Stop any existing containers
docker compose down > /dev/null 2>&1 || true

# Start all services
docker compose up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to initialize (30 seconds)...${NC}"
sleep 30

# Check service health
echo ""
echo -e "${BLUE}🔍 Checking service health...${NC}"

# PostgreSQL (checking localhost)
if pg_isready -h localhost -p 5432 > /dev/null 2>&1 || nc -z localhost 5432 2>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL (localhost:5432)${NC}"
else
    echo -e "${RED}❌ PostgreSQL not accessible on localhost:5432${NC}"
fi

# Redis
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis${NC}"
else
    echo -e "${RED}❌ Redis not ready${NC}"
fi

# Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Elasticsearch${NC}"
else
    echo -e "${YELLOW}⚠️  Elasticsearch not ready (may take more time)${NC}"
fi

# Qdrant (now on port 8060)
if curl -s http://localhost:8060/v1/.well-known/ready > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant${NC}"
else
    echo -e "${YELLOW}⚠️  Qdrant not ready (may take more time)${NC}"
fi

# Check if backend container exists
if docker compose ps | grep -q "backend"; then
    echo -e "${GREEN}✅ Backend API${NC}"
    
    # Run database migrations
    echo ""
    echo -e "${BLUE}🗄️  Running database migrations...${NC}"
    docker compose exec -T backend alembic upgrade head 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Migrations may need manual attention${NC}"
        echo "   Run: docker compose exec backend alembic upgrade head"
    }
else
    echo -e "${YELLOW}⚠️  Backend not in docker compose, starting locally...${NC}"
    
    # Start backend locally using conda env 'indoc'
    echo -e "${BLUE}🔧 Starting backend server (conda env 'indoc')...${NC}"
    if command -v conda >/dev/null 2>&1; then
        eval "$(conda shell.bash hook)" 2>/dev/null || true
        if conda activate indoc 2>/dev/null; then
            (cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &) 
            BACKEND_PID=$!
        else
            echo -e "${RED}❌ Conda env 'indoc' not found. Create and install requirements first.${NC}"
            echo "   conda create -n indoc python=3.10 && conda activate indoc && pip install -r backend/requirements.txt"
            exit 1
        fi
    else
        echo -e "${RED}❌ Conda not found in PATH. Install Miniconda/Anaconda.${NC}"
        exit 1
    fi
fi

# Check Celery workers
if docker compose ps | grep -q "celery_worker.*Up"; then
    echo -e "${GREEN}✅ Celery Workers${NC}"
else
    echo -e "${YELLOW}⚠️  Celery workers not running${NC}"
fi

# Check monitoring services
if docker compose ps | grep -q "flower.*Up"; then
    echo -e "${GREEN}✅ Flower (Celery monitoring)${NC}"
else
    echo -e "${YELLOW}⚠️  Flower not running${NC}"
fi

if docker compose ps | grep -q "prometheus.*Up"; then
    echo -e "${GREEN}✅ Prometheus${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus not running${NC}"
fi

if docker compose ps | grep -q "grafana.*Up"; then
    echo -e "${GREEN}✅ Grafana${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana not running${NC}"
fi

# Start frontend if needed
if [ ! -d "frontend/node_modules" ]; then
    echo ""
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi

echo ""
echo -e "${BLUE}🎨 Starting frontend development server...${NC}"
cd frontend
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 5

# Display access information
echo ""
echo -e "${GREEN}✨ inDoc SaaS Platform is running!${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📍 Access Points:${NC}"
echo "   • Frontend:          http://localhost:5173"
echo "   • Backend API Docs:  http://localhost:8000/api/v1/docs"
echo "   • Flower (Celery):   http://localhost:5555"
echo "   • Grafana:           http://localhost:3030  (changed from 3000)"
echo "   • Prometheus:        http://localhost:9090"
echo "   • Qdrant:          http://localhost:8060  (changed from 8080)"
echo ""
echo -e "${BLUE}📝 Default Credentials:${NC}"
echo "   • Admin:      admin@indoc.local / admin123"
echo "   • Reviewer:   reviewer@indoc.local / admin123"
echo "   • Uploader:   uploader@indoc.local / admin123"
echo ""
echo -e "${BLUE}🎯 New Features Available:${NC}"
echo "   • Document Chat:     Real-time chat with documents"
echo "   • Bulk Upload:       Drag & drop folders or ZIP files"
echo "   • WebSocket Support: Real-time updates"
echo "   • Task Monitoring:   Check background tasks in Flower"
echo "   • Metrics:           View system metrics in Grafana"
echo ""
echo -e "${YELLOW}🛑 To stop all services:${NC}"
echo "   Press Ctrl+C or run: docker compose down"
echo ""

# Handle shutdown
trap cleanup INT TERM

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"
    
    # Kill local processes if they exist
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Stop Docker services
    docker compose down
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Keep script running
while true; do
    sleep 1
done