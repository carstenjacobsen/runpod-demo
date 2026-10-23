"""Append /api/release requests to a CSV file in a RunPod network volume via its S3-compatible API."""
from __future__ import annotations

import csv
import io
import os
import threading
from datetime import datetime, timezone

import boto3
from botocore.exceptions import BotoCoreError, ClientError

HEADER = ["timestamp", "owner", "repo", "summary"]
_lock = threading.Lock()


class LogError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _client_and_target():
    access_key = os.environ.get("RUNPOD_S3_ACCESS_KEY")
    secret_key = os.environ.get("RUNPOD_S3_SECRET_KEY")
    endpoint = os.environ.get("RUNPOD_S3_ENDPOINT")
    region = os.environ.get("RUNPOD_S3_REGION")
    bucket = os.environ.get("RUNPOD_S3_BUCKET")
    if not all((access_key, secret_key, endpoint, region, bucket)):
        raise LogError(
            "Request log is not configured: set RUNPOD_S3_ACCESS_KEY, RUNPOD_S3_SECRET_KEY, "
            "RUNPOD_S3_ENDPOINT, RUNPOD_S3_REGION and RUNPOD_S3_BUCKET.",
            500,
        )
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    return client, bucket, os.environ.get("RUNPOD_S3_LOG_KEY", "release_requests.csv")


def _read_csv(client, bucket: str, key: str) -> str:
    """Return the CSV file's text, or "" if it doesn't exist yet."""
    try:
        return client.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return ""
        raise


def list_release_requests() -> list[dict]:
    """Return all logged requests as [{"date", "owner", "repo", "summary"}, ...]."""
    client, bucket, key = _client_and_target()
    try:
        text = _read_csv(client, bucket, key)
    except (ClientError, BotoCoreError) as e:
        raise LogError(f"Failed to read request log: {e}")
    return [
        {"date": r["timestamp"], "owner": r["owner"], "repo": r["repo"], "summary": r["summary"]}
        for r in csv.DictReader(io.StringIO(text))
    ]


def log_release_request(owner: str, repo: str, summary: str) -> None:
    """Add one row to the CSV log. S3 has no append, so the file is read, extended and re-uploaded."""
    client, bucket, key = _client_and_target()
    row = [datetime.now(timezone.utc).isoformat(timespec="seconds"), owner, repo, summary]

    with _lock:  # serialize read-modify-write within this process
        try:
            existing = _read_csv(client, bucket, key)

            buf = io.StringIO()
            buf.write(existing)
            writer = csv.writer(buf)
            if not existing:
                writer.writerow(HEADER)
            writer.writerow(row)
            client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue().encode("utf-8"),
                              ContentType="text/csv")
        except (ClientError, BotoCoreError) as e:
            raise LogError(f"Failed to write request log: {e}")
