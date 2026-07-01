"""S3-compatible object storage (MinIO in dev) via boto3. Lazy imports."""

from __future__ import annotations

from .config import S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_SECRET_KEY


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name="us-east-1",
        # path-style addressing works with MinIO on localhost
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    from botocore.exceptions import ClientError

    client = _client()
    try:
        client.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=S3_BUCKET)


def put_bytes(key: str, data: bytes, content_type: str = "application/pdf") -> None:
    _client().put_object(Bucket=S3_BUCKET, Key=key, Body=data, ContentType=content_type)


def get_bytes(key: str) -> bytes:
    return _client().get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
