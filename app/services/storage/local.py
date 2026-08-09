from __future__ import annotations

from pathlib import Path
from typing import Optional
import mimetypes

from app.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Filesystem-backed storage for development and single-node setups."""
    
    name = "local"  # Backend identifier

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).resolve()

    def _path_for(self, key: str) -> Path:
        return (self.base_path / key).resolve()

    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, key: str) -> bool:
        return self._path_for(key).exists()

    def delete(self, key: str) -> None:
        p = self._path_for(key)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                # Best-effort delete; ignore errors for local dev
                pass

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        # In local mode we don't presign; return a file:// URL for tooling, though
        return f"file://{self._path_for(key)}"


