#!/bin/bash

# Setup script for using existing localhost PostgreSQL with inDoc
# This creates the necessary database and user in your existing PostgreSQL

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐘 inDoc Local PostgreSQL Setup${NC}"
echo "================================="
echo ""
echo "This script will create the 'indoc' database and user"
echo "in your existing PostgreSQL instance on localhost:5432"
echo ""

# Check if PostgreSQL is running
if ! lsof -i :5432 > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL is not running on localhost:5432${NC}"
    echo "Please start your PostgreSQL instance first"
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL is running on localhost:5432${NC}"

# Get PostgreSQL credentials
echo ""
echo -e "${YELLOW}Enter your PostgreSQL superuser credentials:${NC}"
read -p "PostgreSQL superuser (default: postgres): " PG_SUPERUSER
PG_SUPERUSER=${PG_SUPERUSER:-postgres}

echo -n "PostgreSQL superuser password: "
read -s PG_SUPERUSER_PASSWORD
echo ""

# Database configuration
DB_NAME="indoc"
DB_USER="indoc_user"
echo ""
read -p "Enter password for indoc_user (or press Enter for 'indoc_dev_password'): " DB_PASSWORD
DB_PASSWORD=${DB_PASSWORD:-indoc_dev_password}

echo ""
echo -e "${BLUE}Creating database and user...${NC}"

# Create the SQL commands
SQL_COMMANDS=$(cat <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${DB_USER}') THEN
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    ELSE
        ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\\gexec

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Connect to the database and set up extensions
\\c ${DB_NAME}

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO ${DB_USER};
EOF
)

# Execute the SQL commands
PGPASSWORD=$PG_SUPERUSER_PASSWORD psql -h localhost -U $PG_SUPERUSER -p 5432 <<< "$SQL_COMMANDS"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database setup complete!${NC}"
    echo ""
    echo -e "${BLUE}Database Configuration:${NC}"
    echo "  • Database: ${DB_NAME}"
    echo "  • User: ${DB_USER}"
    echo "  • Password: ${DB_PASSWORD}"
    echo "  • Host: localhost"
    echo "  • Port: 5432"
    echo ""
    
    # Update .env file
    echo -e "${YELLOW}Updating .env file...${NC}"
    
    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        cp .env.example .env
    fi
    
    # Update database settings in .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/^POSTGRES_HOST=.*/POSTGRES_HOST=localhost/" .env
        sed -i '' "s/^POSTGRES_USER=.*/POSTGRES_USER=${DB_USER}/" .env
        sed -i '' "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${DB_PASSWORD}/" .env
        sed -i '' "s/^POSTGRES_DB=.*/POSTGRES_DB=${DB_NAME}/" .env
    else
        # Linux
        sed -i "s/^POSTGRES_HOST=.*/POSTGRES_HOST=localhost/" .env
        sed -i "s/^POSTGRES_USER=.*/POSTGRES_USER=${DB_USER}/" .env
        sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${DB_PASSWORD}/" .env
        sed -i "s/^POSTGRES_DB=.*/POSTGRES_DB=${DB_NAME}/" .env
    fi
    
    echo -e "${GREEN}✅ .env file updated${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Run database migrations:"
    echo "     cd backend && alembic upgrade head"
    echo "  2. Start the application:"
    echo "     make saas"
    echo ""
else
    echo -e "${RED}❌ Database setup failed${NC}"
    echo "Please check your PostgreSQL credentials and try again"
    exit 1
fi