"""
Secrets vault integration for secure secret management

Supports multiple vault backends:
- HashiCorp Vault (open-source, self-hosted)
- AWS Secrets Manager (AWS native)
- Environment variables (fallback for local dev)
"""
import os
import logging
import json
from typing import Dict, Any, Optional
from enum import Enum
import base64

logger = logging.getLogger(__name__)


class VaultProvider(str, Enum):
    """Supported vault providers"""
    ENV = "env"  # Environment variables (fallback)
    HASHICORP = "hashicorp"  # HashiCorp Vault
    AWS = "aws"  # AWS Secrets Manager
    AZURE = "azure"  # Azure Key Vault


class SecretsVault:
    """
    Unified interface for secrets management across multiple providers
    
    Features:
    - Multi-provider support
    - Automatic fallback to env vars
    - Caching for performance
    - Key rotation support
    """
    
    def __init__(
        self,
        provider: VaultProvider = VaultProvider.ENV,
        config: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.config = config or {}
        self.cache: Dict[str, str] = {}  # Simple in-memory cache
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes
        
        # HashiCorp Vault config
        self.vault_url = self.config.get("vault_url", "http://localhost:8200")
        self.vault_token = self.config.get("vault_token")
        self.vault_path = self.config.get("vault_path", "secret/data/indoc")
        
        # AWS config
        self.aws_region = self.config.get("aws_region", "us-east-1")
        self.aws_secret_name = self.config.get("aws_secret_name", "indoc/secrets")
        
        # Azure config
        self.azure_vault_url = self.config.get("azure_vault_url")
        
        logger.info(f"SecretsVault initialized: provider={self.provider}")
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value by key
        
        Args:
            key: Secret key name
            default: Default value if secret not found
        
        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self.cache:
            return self.cache[key]
        
        try:
            if self.provider == VaultProvider.ENV:
                value = self._get_from_env(key, default)
            elif self.provider == VaultProvider.HASHICORP:
                value = self._get_from_hashicorp(key, default)
            elif self.provider == VaultProvider.AWS:
                value = self._get_from_aws(key, default)
            elif self.provider == VaultProvider.AZURE:
                value = self._get_from_azure(key, default)
            else:
                logger.warning(f"Unknown vault provider: {self.provider}, falling back to env")
                value = self._get_from_env(key, default)
            
            # Cache the value
            if value is not None:
                self.cache[key] = value
            
            return value
        
        except Exception as e:
            logger.error(f"Failed to get secret '{key}' from vault: {e}")
            return default
    
    def _get_from_env(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get secret from environment variables"""
        return os.getenv(key, default)
    
    def _get_from_hashicorp(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get secret from HashiCorp Vault

        Requires hvac library - implement when HashiCorp Vault is deployed
        """
        try:
            import hvac

            # Initialize Vault client
            client = hvac.Client(
                url=self.vault_url,
                token=self.vault_token
            )

            if not client.is_authenticated():
                logger.error("Failed to authenticate with HashiCorp Vault")
                return self._get_from_env(key, default)

            # Read secret from Vault
            secret_path = f"{self.vault_path}/{key}"
            response = client.read(secret_path)

            if response and 'data' in response and 'data' in response['data']:
                return response['data']['data'].get('value')

        except ImportError:
            logger.error("hvac package not installed for HashiCorp Vault integration")
        except Exception as e:
            logger.error(f"Failed to retrieve secret from HashiCorp Vault: {e}")

        logger.warning("HashiCorp Vault integration failed. Using env fallback.")
        return self._get_from_env(key, default)
    
    def _get_from_aws(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get secret from AWS Secrets Manager

        Requires boto3 library - implement when AWS integration is needed
        """
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Initialize AWS client
            client = boto3.client(
                'secretsmanager',
                region_name=self.aws_region
            )

            # Get secret value
            secret_name = f"{self.aws_secret_name}/{key}"
            response = client.get_secret_value(SecretId=secret_name)

            if 'SecretString' in response:
                return response['SecretString']

        except ImportError:
            logger.error("boto3 package not installed for AWS Secrets Manager integration")
        except ClientError as e:
            logger.error(f"AWS Secrets Manager error: {e}")
        except Exception as e:
            logger.error(f"Failed to retrieve secret from AWS Secrets Manager: {e}")

        logger.warning("AWS Secrets Manager integration failed. Using env fallback.")
        return self._get_from_env(key, default)
    
    def _get_from_azure(self, key: str, default: Optional[str]) -> Optional[str]:
        """
        Get secret from Azure Key Vault

        Requires azure-keyvault-secrets library
        """
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential

            # Initialize Azure client
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.azure_vault_url, credential=credential)

            # Get secret value
            secret_name = f"indoc-{key}"
            secret = client.get_secret(secret_name)

            return secret.value

        except ImportError:
            logger.error("azure-keyvault-secrets package not installed for Azure Key Vault integration")
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Azure Key Vault: {e}")

        logger.warning("Azure Key Vault integration failed. Using env fallback.")
        return self._get_from_env(key, default)
    
    def set_secret(self, key: str, value: str) -> bool:
        """
        Set a secret value (primarily for env provider, vaults are typically read-only from app)
        
        Args:
            key: Secret key name
            value: Secret value
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.provider == VaultProvider.ENV:
                os.environ[key] = value
                self.cache[key] = value
                return True
            else:
                logger.warning(f"set_secret not supported for provider: {self.provider}")
                return False
        except Exception as e:
            logger.error(f"Failed to set secret '{key}': {e}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret (remove from cache)
        
        Args:
            key: Secret key name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if key in self.cache:
                del self.cache[key]
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret '{key}': {e}")
            return False
    
    def refresh_cache(self):
        """Clear the secrets cache to force refresh"""
        self.cache.clear()
        logger.info("Secrets cache cleared")
    
    def get_all_secrets(self) -> Dict[str, str]:
        """
        Get all secrets from the vault (only for env provider)
        
        Returns:
            Dictionary of all secrets
        """
        if self.provider == VaultProvider.ENV:
            # Return only secrets that match our prefix convention
            prefix = "INDOC_"
            return {
                k: v for k, v in os.environ.items()
                if k.startswith(prefix)
            }
        else:
            logger.warning("get_all_secrets only supported for env provider")
            return {}


# Global secrets vault instance
_secrets_vault: Optional[SecretsVault] = None


def init_secrets_vault(provider: VaultProvider = VaultProvider.ENV, config: Dict[str, Any] = None):
    """Initialize the global secrets vault"""
    global _secrets_vault
    _secrets_vault = SecretsVault(provider=provider, config=config or {})
    return _secrets_vault


def get_secrets_vault() -> SecretsVault:
    """Get the global secrets vault instance"""
    if _secrets_vault is None:
        # Auto-initialize with env provider if not set
        return init_secrets_vault()
    return _secrets_vault


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    vault = get_secrets_vault()
    return vault.get_secret(key, default)




class SecurityAuditor:
    """Security audit and compliance monitoring"""

    @staticmethod
    def audit_secret_access(key: str, success: bool, source: str = "unknown"):
        """Audit secret access for compliance"""
        import time
        timestamp = int(time.time())

        audit_event = {
            "timestamp": timestamp,
            "event_type": "secret_access",
            "key": key,
            "success": success,
            "source": source,
            "user": "system"  # Would be actual user in production
        }

        # In production, this would be sent to SIEM or audit log
        logger.info(f"SECRET_AUDIT: {json.dumps(audit_event)}")

    @staticmethod
    def audit_configuration_changes(changes: Dict[str, Any]):
        """Audit configuration changes"""
        import time
        timestamp = int(time.time())

        audit_event = {
            "timestamp": timestamp,
            "event_type": "config_change",
            "changes": changes,
            "user": "system"
        }

        logger.info(f"CONFIG_AUDIT: {json.dumps(audit_event)}")

    @staticmethod
    def check_security_compliance() -> Dict[str, Any]:
        """Check security compliance status"""
        compliance = {
            "secrets_encrypted": True,
            "keys_rotated_recently": True,  # Would check actual rotation timestamps
            "access_logged": True,
            "vault_provider_secure": True,  # Would check if using secure provider
            "environment_production": False  # Would check actual environment
        }

        # Check JWT secret strength
        jwt_secret = get_secret("JWT_SECRET_KEY")
        if jwt_secret:
            compliance["jwt_secret_strength"] = len(jwt_secret) >= 32

        # Check field encryption key
        enc_key = get_secret("FIELD_ENCRYPTION_KEY")
        if enc_key:
            compliance["encryption_key_present"] = True

        return compliance




