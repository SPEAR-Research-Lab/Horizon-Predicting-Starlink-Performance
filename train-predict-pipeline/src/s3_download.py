"""
Download measurement data and predictions from S3.

Usage:
    python -m src.s3_download --bucket horizon-starlink-data
"""

import argparse
import os
from pathlib import Path

import boto3

from . import logger


def download_s3_folder(bucket: str, prefix: str, local_dir: Path) -> None:
    local_dir.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client("s3")

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in response:
        logger.warning(f"No objects found in s3://{bucket}/{prefix}")
        return

    for obj in response["Contents"]:
        key = obj["Key"]
        filename = key.split("/")[-1]
        if not filename:
            continue
        local_path = local_dir / filename
        logger.info(f"  Downloading {filename}")
        s3.download_file(bucket, key, str(local_path))

    logger.info(f"  Downloaded {len(response['Contents'])} files to {local_dir}")


def run(bucket: str) -> None:
    logger.info(f"Downloading data from s3://{bucket}/")
    download_s3_folder(bucket, "measurements/", Path("/tmp/measurements"))
    download_s3_folder(bucket, "predictions/", Path("/tmp/predictions"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()
    run(args.bucket)
