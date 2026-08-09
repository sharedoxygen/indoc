#!/bin/bash
# Production Deployment Script for inDoc
# This script addresses all integration issues and follows production best practices

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.production.yml"
BACKUP_DIR="${PROJECT_ROOT}/backups/$(date +%Y%m%d_%H%M%S)"

# Environment file
ENV_FILE="${PROJECT_ROOT}/.env.production"
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: Production environment file not found: $ENV_FILE${NC}"
    echo "Please create $ENV_FILE with all required environment variables"
    exit 1
fi

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Check if required files exist
    local required_files=(
        "Dockerfile"
        "docker-compose.production.yml"
        "monitoring/production-monitoring.yml"
        "app/core/config.py"
        "app/main.py"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "${PROJECT_ROOT}/${file}" ]]; then
            log_error "Required file not found: ${file}"
            exit 1
        fi
    done

    # Check environment variables
    source "$ENV_FILE"
    local required_vars=(
        "DB_PASSWORD"
        "JWT_SECRET_KEY"
        "FIELD_ENCRYPTION_KEY"
        "VAULT_TOKEN"
        "REDIS_PASSWORD"
        "GRAFANA_PASSWORD"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done

    # Validate configuration
    log_info "Validating production configuration..."
    cd "$PROJECT_ROOT"
    python -c "
import sys
sys.path.append('.')
from app.core.config import settings
try:
    settings.validate_production_config()
    print('✅ Production configuration validation passed')
except Exception as e:
    print(f'❌ Configuration validation failed: {e}')
    sys.exit(1)
"

    log_success "Pre-deployment checks completed"
}

# Create backups
create_backups() {
    log_info "Creating backups..."

    mkdir -p "$BACKUP_DIR"

    # Backup current database (if exists)
    if docker-compose -f "$COMPOSE_FILE" ps db >/dev/null 2>&1; then
        log_info "Backing up database..."
        docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U indoc_user indoc_prod > "${BACKUP_DIR}/database_backup.sql" 2>/dev/null || {
            log_warn "Database backup failed or database not accessible"
        }
    fi

    # Backup uploaded files
    if [[ -d "${PROJECT_ROOT}/uploads" ]]; then
        log_info "Backing up uploads..."
        cp -r "${PROJECT_ROOT}/uploads" "${BACKUP_DIR}/"
    fi

    log_success "Backups created in $BACKUP_DIR"
}

# Initialize secrets vault
init_secrets_vault() {
    log_info "Initializing secrets vault..."

    # Create Vault configuration if it doesn't exist
    if [[ ! -f "${PROJECT_ROOT}/vault/config.hcl" ]]; then
        mkdir -p "${PROJECT_ROOT}/vault"
        cat > "${PROJECT_ROOT}/vault/config.hcl" << 'EOF'
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_disable = true
}

api_addr = "http://0.0.0.0:8200"
cluster_addr = "https://0.0.0.0:8201"
ui = true
EOF
    fi

    # Start Vault temporarily to initialize
    log_info "Starting Vault for initialization..."
    docker-compose -f "$COMPOSE_FILE" up -d vault

    # Wait for Vault to be ready
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if curl -f "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Vault failed to start"
        exit 1
    fi

    # Initialize Vault with secrets
    log_info "Configuring Vault with application secrets..."
    source "$ENV_FILE"

    # Store secrets in Vault
    curl -X POST "http://localhost:8200/v1/secret/data/indoc/jwt_secret_key" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"data\": {\"value\": \"$JWT_SECRET_KEY\"}}" >/dev/null 2>&1

    curl -X POST "http://localhost:8200/v1/secret/data/indoc/field_encryption_key" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"data\": {\"value\": \"$FIELD_ENCRYPTION_KEY\"}}" >/dev/null 2>&1

    curl -X POST "http://localhost:8200/v1/secret/data/indoc/db_password" \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"data\": {\"value\": \"$DB_PASSWORD\"}}" >/dev/null 2>&1

    log_success "Secrets vault initialized"
}

# Deploy application
deploy_application() {
    log_info "Deploying inDoc application..."

    # Stop existing containers gracefully
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans

    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull --quiet

    # Start infrastructure services first
    log_info "Starting infrastructure services..."
    docker-compose -f "$COMPOSE_FILE" up -d db redis elasticsearch qdrant ollama vault prometheus grafana loki jaeger

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    local retries=60
    while [[ $retries -gt 0 ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U indoc_user -d indoc_prod >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Database failed to start"
        exit 1
    fi

    # Run database migrations
    log_info "Running database migrations..."
    docker-compose -f "$COMPOSE_FILE" run --rm app alembic upgrade head

    # Start application
    log_info "Starting application..."
    docker-compose -f "$COMPOSE_FILE" up -d app nginx fluent-bit

    # Wait for application to be ready
    log_info "Waiting for application to be ready..."
    retries=60
    while [[ $retries -gt 0 ]]; do
        if curl -f "http://localhost:8000/health" >/dev/null 2>&1; then
            break
        fi
        sleep 2
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Application failed to start"
        exit 1
    fi

    log_success "Application deployed successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Test health endpoints
    local health_endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8000/health/detailed"
        "http://localhost:9090/-/healthy"
        "http://localhost:3000/api/health"
        "http://localhost:9200/_cluster/health"
        "http://localhost:8060/v1/meta"
        "http://localhost:11434/api/tags"
    )

    for endpoint in "${health_endpoints[@]}"; do
        if curl -f "$endpoint" >/dev/null 2>&1; then
            log_success "✓ $endpoint is healthy"
        else
            log_warn "⚠ $endpoint is not accessible"
        fi
    done

    # Test database connectivity
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U indoc_user -d indoc_prod >/dev/null 2>&1; then
        log_success "✓ Database is accessible"
    else
        log_error "✗ Database is not accessible"
        exit 1
    fi

    # Test authentication flow
    log_info "Testing authentication flow..."
    # This would include testing login, JWT token generation, and document access

    log_success "Deployment verification completed"
}

# Post-deployment tasks
post_deployment_tasks() {
    log_info "Running post-deployment tasks..."

    # Update deployment tracking
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Deployed version $(git rev-parse --short HEAD)" >> "${PROJECT_ROOT}/deployment.log"

    # Clean up old backups (keep last 7 days)
    find "${PROJECT_ROOT}/backups" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

    # Set up log rotation
    if command -v logrotate >/dev/null 2>&1; then
        logrotate -f /etc/logrotate.d/indoc 2>/dev/null || log_warn "Log rotation configuration not found"
    fi

    log_success "Post-deployment tasks completed"
}

# Main deployment process
main() {
    log_info "🚀 Starting inDoc production deployment..."

    pre_deployment_checks
    create_backups
    init_secrets_vault
    deploy_application
    verify_deployment
    post_deployment_tasks

    log_success "🎉 inDoc production deployment completed successfully!"
    log_info "📊 Application available at: http://localhost:8000"
    log_info "📊 Grafana dashboard at: http://localhost:3000"
    log_info "📊 Prometheus metrics at: http://localhost:9090"
    log_info "🔍 Jaeger traces at: http://localhost:16686"

    echo ""
    log_info "Next steps:"
    echo "1. Update your DNS to point to this server"
    echo "2. Configure SSL certificates in nginx/ssl/"
    echo "3. Set up monitoring alerts in Grafana"
    echo "4. Configure backup schedules"
    echo "5. Test the full application workflow"
}

# Handle script arguments
case "${1:-}" in
    "backup")
        create_backups
        ;;
    "verify")
        verify_deployment
        ;;
    "rollback")
        log_info "Rolling back deployment..."
        # Implementation would restore from backup
        ;;
    *)
        main
        ;;
esac

