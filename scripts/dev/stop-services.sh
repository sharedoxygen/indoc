#!/bin/bash

# inDoc Complete Shutdown Script
# Stops ALL services regardless of how they were started

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${RED}🛑 Stopping ALL inDoc Services${NC}"
echo "=================================="
echo ""

# Function to kill process by port
kill_port() {
    local port=$1
    local service=$2
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}Stopping $service on port $port (PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null || true
        echo -e "${GREEN}✅ $service stopped${NC}"
    fi
}

# 1. Stop Docker Compose services
echo -e "${BLUE}1. Stopping Docker Compose services...${NC}"
if docker compose ps -q 2>/dev/null | grep -q .; then
    docker compose down -v
    echo -e "${GREEN}✅ Docker services stopped and volumes removed${NC}"
else
    echo -e "${YELLOW}No Docker Compose services running${NC}"
fi

# 2. Stop any remaining Docker containers with 'indoc' in the name
echo ""
echo -e "${BLUE}2. Stopping any remaining inDoc containers...${NC}"
docker ps -q --filter "name=indoc" | while read container; do
    echo -e "${YELLOW}Stopping container: $container${NC}"
    docker stop $container 2>/dev/null || true
    docker rm $container 2>/dev/null || true
done
echo -e "${GREEN}✅ All inDoc containers stopped${NC}"

# 3. Kill processes on specific ports
echo ""
echo -e "${BLUE}3. Stopping services on known ports...${NC}"

# Backend API
kill_port 8000 "Backend API"

# Frontend
kill_port 5173 "Frontend Dev Server"
kill_port 3000 "Frontend (alternate)"

# Elasticsearch
kill_port 9200 "Elasticsearch"

# Qdrant
kill_port 8080 "Qdrant"

# Redis
kill_port 6379 "Redis"

# PostgreSQL
kill_port 5432 "PostgreSQL"

# Flower (Celery monitoring)
kill_port 5555 "Flower"

# Grafana
kill_port 3000 "Grafana"

# Prometheus
kill_port 9090 "Prometheus"

# 4. Kill specific processes by name
echo ""
echo -e "${BLUE}4. Stopping processes by name...${NC}"

# Kill uvicorn (backend)
pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo -e "${GREEN}✅ Uvicorn stopped${NC}" || true

# Kill npm/node processes for inDoc
pkill -f "npm.*inDoc" 2>/dev/null && echo -e "${GREEN}✅ NPM processes stopped${NC}" || true
pkill -f "node.*inDoc" 2>/dev/null && echo -e "${GREEN}✅ Node processes stopped${NC}" || true

# Kill Celery workers
pkill -f "celery.*worker" 2>/dev/null && echo -e "${GREEN}✅ Celery workers stopped${NC}" || true
pkill -f "celery.*beat" 2>/dev/null && echo -e "${GREEN}✅ Celery beat stopped${NC}" || true

# Kill Python processes running main.py or run_server.py
pkill -f "python.*main.py" 2>/dev/null && echo -e "${GREEN}✅ Python main stopped${NC}" || true
pkill -f "python.*run_server.py" 2>/dev/null && echo -e "${GREEN}✅ Python server stopped${NC}" || true

# 5. Stop Ollama if it was started for inDoc
echo ""
echo -e "${BLUE}5. Checking Ollama...${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Ollama is running. Stop it? (y/n)${NC}"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -x "ollama" 2>/dev/null && echo -e "${GREEN}✅ Ollama stopped${NC}" || true
    else
        echo -e "${BLUE}Ollama left running${NC}"
    fi
else
    echo -e "${YELLOW}Ollama not running${NC}"
fi

# 6. Clean up temporary files
echo ""
echo -e "${BLUE}6. Cleaning up temporary files...${NC}"
rm -f backend/run_server.py 2>/dev/null || true
rm -rf backend/__pycache__ 2>/dev/null || true
rm -rf frontend/.next 2>/dev/null || true
echo -e "${GREEN}✅ Temporary files cleaned${NC}"

# 7. Final verification
echo ""
echo -e "${BLUE}7. Verifying all services are stopped...${NC}"

# Check Docker
if docker compose ps 2>/dev/null | grep -q "indoc"; then
    echo -e "${RED}⚠️  Some Docker services may still be running${NC}"
else
    echo -e "${GREEN}✅ No Docker services running${NC}"
fi

# Check ports
all_clear=true
for port in 8000 5173 9200 8080 6379 5432 5555 3000 9090; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port is still in use${NC}"
        all_clear=false
    fi
done

if [ "$all_clear" = true ]; then
    echo -e "${GREEN}✅ All ports are clear${NC}"
fi

echo ""
echo -e "${GREEN}✨ All inDoc services have been stopped!${NC}"
echo ""
echo -e "${BLUE}To restart the services, use:${NC}"
echo "  make saas          # Full SaaS platform"
echo "  make dev           # Basic development"
echo "  ./start-saas.sh    # Alternative startup"
echo ""