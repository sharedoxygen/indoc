from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class StorageBackend(ABC):
    """Abstract interface for object storage backends.

    Implementations should provide simple primitives that callers can use
    without knowledge of the underlying provider (local filesystem, S3, etc.).
    """

    @abstractmethod
    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        """Store raw bytes at the specified key."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if an object exists at the specified key."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the object at the specified key if it exists."""
        raise NotImplementedError

    @abstractmethod
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned HTTP GET URL for the specified key."""
        raise NotImplementedError


def build_object_key(tenant_id: Optional[str], file_hash: str, file_extension: str, prefix: Optional[str] = None) -> str:
    """Create a stable, content-addressed object key.

    Example: tenantA/ab/abcdef...1234.pdf or with prefix: uploads/tenantA/ab/...
    """
    safe_tenant = str(tenant_id) if tenant_id else "public"
    ext = file_extension.lstrip(".") if file_extension else "bin"
    key_parts = [p for p in [prefix, safe_tenant, file_hash[:2], f"{file_hash}.{ext}"] if p]
    return "/".join(key_parts)


