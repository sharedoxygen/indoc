from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend


class StorageFactory:
    """Factory for creating and managing storage backends"""
    
    def __init__(self):
        self.primary_backend = self._get_primary_backend()
        self.secondary_backend = self._get_secondary_backend()
    
    def _get_primary_backend(self) -> Optional[StorageBackend]:
        """Return the primary storage backend instance based on configuration."""
        if settings.STORAGE_BACKEND == "local":
            return LocalStorageBackend(settings.OBJECT_STORAGE_LOCAL_BASE)
        if settings.STORAGE_BACKEND == "s3":
            try:
                from app.services.storage.s3 import S3StorageBackend
                return S3StorageBackend(
                    bucket=settings.S3_BUCKET,
                    region=settings.S3_REGION,
                    endpoint_url=settings.S3_ENDPOINT_URL or None,
                    access_key=settings.S3_ACCESS_KEY_ID,
                    secret_key=settings.S3_SECRET_ACCESS_KEY,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to initialize S3 primary storage: {e}")
                return None
        return None
    
    def _get_secondary_backend(self) -> Optional[StorageBackend]:
        """Return the secondary storage for dual-write, if enabled."""
        if not settings.OBJECT_STORAGE_DUAL_WRITE:
            return None
        # Secondary is the opposite of primary if configured
        if settings.STORAGE_BACKEND == "s3":
            return LocalStorageBackend(settings.OBJECT_STORAGE_LOCAL_BASE)
        if settings.STORAGE_BACKEND == "local":
            try:
                from app.services.storage.s3 import S3StorageBackend
                return S3StorageBackend(
                    bucket=settings.S3_BUCKET,
                    region=settings.S3_REGION,
                    endpoint_url=settings.S3_ENDPOINT_URL or None,
                    access_key=settings.S3_ACCESS_KEY_ID,
                    secret_key=settings.S3_SECRET_ACCESS_KEY,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to initialize S3 secondary storage: {e}")
                return None
        return None
    
    def get_primary_backend(self) -> Optional[StorageBackend]:
        """Get the primary storage backend"""
        return self.primary_backend
    
    def get_secondary_backend(self) -> Optional[StorageBackend]:
        """Get the secondary storage backend (for dual-write)"""
        return self.secondary_backend
    
    def get_s3_backend(self) -> Optional[StorageBackend]:
        """Get S3 backend (either primary or secondary)"""
        if isinstance(self.primary_backend, type(None)):
            return None
        if self.primary_backend.name == "s3":
            return self.primary_backend
        if self.secondary_backend and self.secondary_backend.name == "s3":
            return self.secondary_backend
        return None


# Legacy function-based API (for backwards compatibility)
def get_primary_storage() -> Optional[StorageBackend]:
    """Return the primary storage backend instance based on configuration."""
    factory = StorageFactory()
    return factory.get_primary_backend()


def get_secondary_storage() -> Optional[StorageBackend]:
    """Return the secondary storage for dual-write, if enabled."""
    factory = StorageFactory()
    return factory.get_secondary_backend()


def build_object_key(tenant_id: str, file_hash: str, file_ext: str, prefix: str = "uploads") -> str:
    """Build a consistent object key for storage backends"""
    from app.services.storage.base import build_object_key as _build_key
    return _build_key(tenant_id, file_hash, file_ext, prefix)
