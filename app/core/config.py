"""
Configuration management for inDoc
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
from pathlib import Path
import os
import yaml


class Settings(BaseSettings):
    # Pydantic v2 config
    model_config = ConfigDict(env_file=[".env", "../.env"], case_sensitive=True, extra='ignore')

    # Application
    APP_NAME: str = "inDoc"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # File Upload
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB default
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "indoc"
    POSTGRES_USER: str = "indoc_user"
    POSTGRES_PASSWORD: str = "indoc_dev_password"
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200")
    ELASTICSEARCH_INDEX: str = Field(default="indoc_documents")
    
    # Qdrant (Vector Search)
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_COLLECTION: str = Field(default="documents")
    QDRANT_VECTOR_SIZE: int = Field(default=384)
    QDRANT_DISTANCE: str = Field(default="Cosine")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")
    
    # LLM Providers (per AI Guide: no hard-coding)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="gpt-oss:20b")
    LLM_TIMEOUT_S: int = Field(default=30, description="LLM request timeout in seconds")
    
    # OpenAI Fallback (optional, cloud-based)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for fallback")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model to use")
    
    # Answer Grounding (AI Guide §3: prevent hallucination)
    MIN_REQUIRED_SOURCES: int = Field(default=3, description="Minimum document sources required for grounded answers")
    MIN_GROUNDING_CONFIDENCE: float = Field(default=0.7, description="Minimum confidence score for answer grounding")
    CONVERSATION_HISTORY_LENGTH: int = Field(default=6, description="Number of previous messages to include in context")
    
    # Security
    JWT_SECRET_KEY: str = Field(default="")  # Will be set by key manager
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    JWT_REFRESH_EXPIRATION_DAYS: int = 30  # Refresh tokens last 30 days
    
    # MFA Settings
    MFA_ENABLED: bool = Field(
        default=False,  # Disabled by default for local dev
        description="Enable/disable MFA enforcement"
    )
    MFA_REQUIRED_ROLES: List[str] = Field(
        default=["Admin", "Manager"],
        description="Roles that require MFA when enabled"
    )
    MFA_ISSUER_NAME: str = Field(
        default="inDoc",
        description="TOTP issuer name shown in authenticator apps"
    )
    
    # Encryption
    FIELD_ENCRYPTION_KEY: str = Field(default="")  # Will be set by key manager
    ENABLE_FIELD_ENCRYPTION: bool = True
    
    # Environment Detection
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment: development, staging, production"
    )

    # Security Headers
    CSP_REPORT_ONLY: bool = Field(
        default=True,  # Start in report-only mode for testing
        description="Run CSP in report-only mode (doesn't block, just reports violations)"
    )
    CSP_REPORT_URI: Optional[str] = Field(
        default=None,
        description="URI to send CSP violation reports to"
    )
    SECURITY_HEADERS_ENABLED: bool = Field(
        default=True,
        description="Enable security headers middleware"
    )
    
    # Secrets Vault
    VAULT_ENABLED: bool = Field(
        default=False,
        description="Enable secrets vault for key management"
    )
    VAULT_PROVIDER: str = Field(
        default="env",
        description="Vault provider: env, hashicorp, aws, azure"
    )
    VAULT_URL: Optional[str] = Field(
        default=None,
        description="Vault server URL (for HashiCorp Vault)"
    )
    VAULT_TOKEN: Optional[str] = Field(
        default=None,
        description="Vault authentication token"
    )
    
    def __init__(self, **kwargs):
        # Merge YAML defaults and local overrides first
        yaml_config = {}
        try:
            with open(Path(__file__).resolve().parent.parent.parent / 'config' / 'default.yaml', 'r') as f:
                yaml_config = yaml.safe_load(f) or {}
            local_path = Path(__file__).resolve().parent.parent.parent / 'config' / 'local.yaml'
            if local_path.exists():
                local_cfg = yaml.safe_load(local_path.read_text()) or {}
                # shallow merge local over default
                def merge(a, b):
                    for k, v in (b or {}).items():
                        if isinstance(v, dict) and isinstance(a.get(k), dict):
                            merge(a[k], v)
                        else:
                            a[k] = v
                    return a
                yaml_config = merge(yaml_config, local_cfg)
        except Exception:
            yaml_config = yaml_config or {}

        # Map YAML into our fields if not provided via kwargs/env
        mapped = {}
        def g(path, default=None):
            cur = yaml_config
            for p in path:
                if not isinstance(cur, dict) or p not in cur: return default
                cur = cur[p]
            return cur
        mapped.update({
            'APP_NAME': g(['app','name'], self.APP_NAME if hasattr(self, 'APP_NAME') else 'inDoc'),
            'APP_VERSION': g(['app','version'], self.APP_VERSION if hasattr(self, 'APP_VERSION') else '1.0.0'),
            'API_PREFIX': g(['api','prefix'], self.API_PREFIX if hasattr(self, 'API_PREFIX') else '/api/v1'),
            'API_HOST': g(['server','host'], self.API_HOST if hasattr(self, 'API_HOST') else '0.0.0.0'),
            'API_PORT': g(['server','port'], self.API_PORT if hasattr(self, 'API_PORT') else 8000),
            'TEMP_REPO_PATH': Path(g(['storage','temp_path'], './tmp/indoc_temp')).resolve(),
            'STORAGE_PATH': Path(g(['storage','storage_path'], './data/storage')).resolve(),
            'CORS_ORIGINS': g(['cors','origins'], ["http://localhost:5173", "http://localhost:3000"]),
            'ELASTICSEARCH_URL': g(['search','elasticsearch_url'], 'http://localhost:9200'),
            'ELASTICSEARCH_INDEX': g(['search','elasticsearch_index'], 'indoc_documents'),
            'QDRANT_URL': g(['search','qdrant_url'], 'http://localhost:6333'),
            'QDRANT_COLLECTION': g(['search','qdrant_collection'], 'documents'),
            'QDRANT_VECTOR_SIZE': g(['search','qdrant_vector_size'], 384),
            'QDRANT_DISTANCE': g(['search','qdrant_distance'], 'Cosine'),
            'REDIS_URL': g(['redis','url'], 'redis://localhost:6379'),
            'CELERY_BROKER_URL': g(['celery','broker_url'], 'redis://localhost:6379/0'),
            'CELERY_RESULT_BACKEND': g(['celery','result_backend'], 'redis://localhost:6379/0'),
            'OLLAMA_BASE_URL': g(['ollama','base_url'], 'http://localhost:11434'),
            'OLLAMA_MODEL': g(['ollama','model'], 'llama2'),
            # Object storage
            'STORAGE_BACKEND': g(['object_storage','backend'], 'local'),
            'OBJECT_STORAGE_DUAL_WRITE': g(['object_storage','dual_write'], False),
            'OBJECT_STORAGE_LOCAL_BASE': Path(g(['object_storage','local_base'], './data/objects')),
            'S3_BUCKET': g(['object_storage','s3','bucket'], 'shaoxy-indoc'),
            'S3_REGION': g(['object_storage','s3','region'], 'us-east-1'),
            'S3_ENDPOINT_URL': g(['object_storage','s3','endpoint_url'], ''),
            'S3_ACCESS_KEY_ID': g(['object_storage','s3','access_key_id'], os.getenv('S3_ACCESS_KEY_ID', 'minioadmin')),
            'S3_SECRET_ACCESS_KEY': g(['object_storage','s3','secret_access_key'], os.getenv('S3_SECRET_ACCESS_KEY', 'minioadmin')),
            'S3_PRESIGN_TTL_S': g(['object_storage','s3','presign_ttl_s'], 3600),
            'S3_PREFIX': g(['object_storage','s3','prefix'], 'file-storage'),
        })

        # env/kwargs should override YAML
        mapped.update(kwargs)
        super().__init__(**mapped)
        # Initialize production keys if not provided
        self._initialize_production_keys()
    
    def _initialize_production_keys(self):
        """Initialize production-grade keys using key manager"""
        try:
            from app.core.key_management import get_production_keys

            production_keys = get_production_keys()

            # Set JWT secret if not provided via environment
            if not self.JWT_SECRET_KEY:
                self.JWT_SECRET_KEY = production_keys['jwt_secret_key']

            # Set field encryption key if not provided via environment
            if not self.FIELD_ENCRYPTION_KEY:
                self.FIELD_ENCRYPTION_KEY = production_keys['field_encryption_key']

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize production keys: {e}")

            # Fallback to environment variables or generate temporary keys
            if not self.JWT_SECRET_KEY:
                self.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(32).hex())
            if not self.FIELD_ENCRYPTION_KEY:
                from cryptography.fernet import Fernet
                import base64
                self.FIELD_ENCRYPTION_KEY = base64.urlsafe_b64encode(Fernet.generate_key()).decode()

    def validate_production_config(self):
        """Validate configuration for production deployment"""
        errors = []

        if self.ENVIRONMENT == "production":
            # Critical security checks for production
            if len(self.JWT_SECRET_KEY) < 32:
                errors.append("JWT_SECRET_KEY must be at least 32 characters in production")

            if not self.VAULT_ENABLED:
                errors.append("Secrets vault should be enabled in production")

            if not self.SECURITY_HEADERS_ENABLED:
                errors.append("Security headers should be enabled in production")

            if self.CSP_REPORT_ONLY:
                errors.append("CSP should not be in report-only mode in production")

            if self.DEBUG:
                errors.append("DEBUG should be disabled in production")

            if self.API_HOST == "0.0.0.0":
                errors.append("API_HOST should be configured for production")

        if errors:
            error_msg = f"Production configuration validation failed: {'; '.join(errors)}"
            import logging
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            raise ValueError(error_msg)

        return True
    
    # Storage (no side effects here)
    TEMP_REPO_PATH: Path = Path("./tmp/indoc_temp").resolve()
    STORAGE_PATH: Path = Path("./data/storage").resolve()
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "txt", "html", 
        "xml", "json", "eml", "png", "jpg", "jpeg", "tiff"
    ]

    # Object Storage
    STORAGE_BACKEND: str = Field(
        default="local",  # local | s3
        description="Primary storage backend"
    )
    OBJECT_STORAGE_LOCAL_BASE: Path = Field(
        default=Path("./data/objects"),
        description="Base directory for local object storage"
    )
    OBJECT_STORAGE_DUAL_WRITE: bool = Field(
        default=False,
        description="If true, write to secondary backend as well (for migration)"
    )
    # S3-compatible settings (works with MinIO as well)
    S3_BUCKET: str = Field(default="indoc-dev")
    S3_REGION: str = Field(default="us-east-1")
    S3_ENDPOINT_URL: str = Field(default="http://localhost:9000")
    S3_ACCESS_KEY_ID: str = Field(default="minioadmin")
    S3_SECRET_ACCESS_KEY: str = Field(default="minioadmin")
    S3_PRESIGN_TTL_S: int = Field(default=3600)
    S3_PREFIX: str = Field(default="uploads")
    
    # Email Ingestion
    EMAIL_IMAP_SERVER: Optional[str] = None
    EMAIL_IMAP_PORT: int = 993
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    # Observability
    ENABLE_TELEMETRY: bool = True
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    DATADOG_API_KEY: Optional[str] = None
    GRAFANA_CLOUD_API_KEY: Optional[str] = None
    
    # Compliance
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    ENABLE_AUDIT_LOGGING: bool = True
    
    # SIEM Export
    SIEM_ENABLED: bool = Field(
        default=False,
        description="Enable SIEM export for audit logs"
    )
    SIEM_PROVIDER: str = Field(
        default="file",
        description="SIEM provider: file, syslog, cloudwatch, splunk, datadog"
    )
    SIEM_LOG_FILE_PATH: str = Field(
        default="./logs/audit_siem.jsonl",
        description="Path for file-based SIEM export"
    )
    SIEM_SYSLOG_HOST: str = Field(
        default="localhost",
        description="Syslog server hostname"
    )
    SIEM_SYSLOG_PORT: int = Field(
        default=514,
        description="Syslog server port"
    )
    SIEM_SPLUNK_HEC_URL: Optional[str] = Field(
        default=None,
        description="Splunk HTTP Event Collector URL, e.g. https://splunk.example.com:8088/services/collector/event"
    )
    SIEM_SPLUNK_HEC_TOKEN: Optional[str] = Field(
        default=None,
        description="Splunk HEC authentication token"
    )
    SIEM_DATADOG_API_URL: str = Field(
        default="https://http-intake.logs.datadoghq.com/api/v2/logs",
        description="Datadog Logs intake API endpoint"
    )
    SIEM_CLOUDWATCH_LOG_GROUP: Optional[str] = Field(
        default=None,
        description="AWS CloudWatch Logs log group name"
    )
    SIEM_CLOUDWATCH_LOG_STREAM: Optional[str] = Field(
        default=None,
        description="AWS CloudWatch Logs log stream name"
    )
    SIEM_CLOUDWATCH_REGION: str = Field(
        default="us-east-1",
        description="AWS region for the CloudWatch Logs export"
    )
    
    # Performance
    SEARCH_TIMEOUT_MS: int = 200
    RERANK_TIMEOUT_MS: int = 100
    # LLM_TIMEOUT_S moved to LLM Providers section (line 54)
    
    # Virus Scanning - Modern Multi-Layer Approach
    ENABLE_VIRUS_SCANNING: bool = Field(
        default=True,
        description="Enable fast local virus scanning (always recommended)"
    )
    
    # Legacy ClamAV (being phased out)
    ENABLE_CLAMAV: bool = Field(
        default=False,
        description="Enable ClamAV deep scanning (deprecated, use YARA instead)"
    )
    
    # Modern scanning layers
    ENABLE_YARA_RULES: bool = Field(
        default=False,
        description="Enable YARA rule-based scanning (fast, customizable)"
    )
    ENABLE_VIRUSTOTAL: bool = Field(
        default=False,
        description="Enable VirusTotal cloud scanning (requires API key)"
    )
    VIRUSTOTAL_API_KEY: Optional[str] = Field(
        default=None,
        description="VirusTotal API key for cloud scanning"
    )
    VIRUSTOTAL_ASYNC: bool = Field(
        default=True,
        description="Run VirusTotal scans asynchronously (non-blocking)"
    )
    
    # Scanning behavior
    VIRUS_SCAN_TIMEOUT: int = Field(
        default=30,
        description="Virus scan timeout in seconds"
    )
    VIRUS_SCAN_FAIL_ON_ERROR: bool = Field(
        default=False,
        description="Fail upload if virus scan errors (strict mode for production)"
    )
    USE_MODERN_SCANNER: bool = Field(
        default=False,
        description="Use modern scanner instead of ClamAV (recommended)"
    )
    
    # Caching
    ENABLE_REDIS_CACHE: bool = True
    CACHE_TTL_DOCUMENTS: int = 1800  # 30 minutes
    CACHE_TTL_LLM_RESPONSES: int = 3600  # 1 hour
    CACHE_TTL_SEARCH_RESULTS: int = 600  # 10 minutes
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    @field_validator("TEMP_REPO_PATH", "STORAGE_PATH", mode="before")
    @classmethod
    def ensure_path_type(cls, v):
        # Only convert to Path, do not create directories here
        return Path(v)


settings = Settings()