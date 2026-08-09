"""
Storage abstraction layer for inDoc
"""
from .base import StorageBackend, build_object_key
from .local import LocalStorageBackend
from .s3 import S3StorageBackend
from .factory import StorageFactory

__all__ = [
    "StorageBackend",
    "build_object_key",
    "LocalStorageBackend",
    "S3StorageBackend",
    "StorageFactory",
]

