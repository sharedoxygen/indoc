#!/bin/bash

# Database Setup Script for inDoc
# This script initializes the PostgreSQL database with tables and users

echo "🗄️  inDoc Database Setup"
echo "========================"
echo ""

if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    echo "POSTGRES_PASSWORD is required"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if PostgreSQL is running
if ! docker compose ps | grep -q "postgres.*Up"; then
    echo "🐳 Starting PostgreSQL..."
    docker compose up -d postgres
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 10
fi

# Wait for PostgreSQL to be ready
echo "🔍 Checking PostgreSQL connection..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U indoc_user -d indoc > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "⏳ Waiting for PostgreSQL... ($i/30)"
    sleep 1
done

# Initialize database with Python script
echo "🔧 Initializing database tables and users..."
cd backend

# Create a temporary Python script if init_db.py doesn't exist
if [ ! -f "init_db.py" ]; then
    echo "Creating database initialization script..."
    cat > temp_init_db.py << 'EOF'
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection parameters
DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "indoc",
    "user": "indoc_user",
    "password": os.environ["POSTGRES_PASSWORD"]
}

def init_database():
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_PARAMS)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("Connected to database successfully!")
        
        # Create user_role enum if it doesn't exist
        cur.execute("""
            DO $$ BEGIN
                CREATE TYPE user_role AS ENUM ('Admin', 'Reviewer', 'Uploader', 'Viewer', 'Compliance');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(255),
                hashed_password VARCHAR(255) NOT NULL,
                role user_role NOT NULL DEFAULT 'Viewer',
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create documents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                uuid UUID DEFAULT gen_random_uuid() UNIQUE,
                filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash VARCHAR(64),
                storage_path VARCHAR(500) NOT NULL,
                temp_path VARCHAR(500),
                status VARCHAR(50) DEFAULT 'pending',
                error_message TEXT,
                virus_scan_status VARCHAR(50) DEFAULT 'pending',
                virus_scan_result JSONB,
                title VARCHAR(500),
                description TEXT,
                tags JSONB,
                custom_metadata JSONB,
                full_text TEXT,
                extracted_data JSONB,
                language VARCHAR(10),
                elasticsearch_id VARCHAR(100),
                qdrant_id VARCHAR(100),
                encrypted_fields JSONB,
                access_level VARCHAR(50) DEFAULT 'private',
                uploaded_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create audit_logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                user_email VARCHAR(255) NOT NULL,
                user_role VARCHAR(50) NOT NULL,
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(100) NOT NULL,
                resource_id VARCHAR(100),
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                request_method VARCHAR(10),
                request_path VARCHAR(500),
                request_params JSONB,
                response_status INTEGER,
                response_time_ms INTEGER,
                details JSONB,
                error_message TEXT,
                data_classification VARCHAR(50),
                compliance_tags JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_action ON audit_logs(user_id, action);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_uuid ON documents(uuid);")
        
        print("✅ Database tables created successfully!")
        print("Users are not seeded here. Set ADMIN_PASSWORD and run tools/init_db.py.")
        
        conn.commit()
        
        # List users
        cur.execute("SELECT email, username, role FROM users;")
        users = cur.fetchall()
        
        print("\n📋 Users in database:")
        print("-" * 50)
        for user in users:
            print(f"  Email: {user[0]:<25} Role: {user[2]}")
        print("-" * 50)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if init_database():
        print("\n✅ Database setup completed successfully!")
        print("Set user passwords via ADMIN_PASSWORD (and related env vars). Do not commit them.")
    else:
        print("\n❌ Database setup failed!")
EOF
    python3 temp_init_db.py
    rm temp_init_db.py
else
    python3 init_db.py
fi

cd ..

echo ""
echo "✅ Database setup complete!"
echo ""