from __future__ import annotations

from typing import Optional

from app.services.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    """S3-compatible backend using boto3.

    Note: We import boto3 lazily to avoid hard dependency when not configured.
    """
    
    name = "s3"  # Backend identifier

    def __init__(self, bucket: str, region: Optional[str] = None, endpoint_url: Optional[str] = None, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        import boto3  # type: ignore

        session = boto3.session.Session()
        self._s3 = session.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._bucket = bucket

    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )


