from enum import StrEnum
import io

import boto3
import pandas as pd

from config import logger


class S3Directory(StrEnum):
    MEASUREMENTS = "measurements"
    PREDICTIONS = "predictions"


class AwsS3Client:
    def __init__(self, bucket_name: str) -> None:
        self._s3_bucket = boto3.resource("s3").Bucket(bucket_name)
        self._measurement_files: list[str] | None = None

    def _get_key(self, directory: S3Directory, file: str) -> str:
        return f"{directory}/{file}"

    def _get_object_names_by_directory(self, directory: S3Directory) -> list[str]:
        return [obj.key for obj in self._s3_bucket.objects.filter(Prefix=f"{directory}/")]

    def get_measurements_files(self, refetch: bool = False) -> list[str]:
        if self._measurement_files is None or refetch:
            self._measurement_files = self._get_object_names_by_directory(S3Directory.MEASUREMENTS)
        return self._measurement_files

    def get_dataframe(self, directory: S3Directory, file: str) -> pd.DataFrame:
        obj = self._s3_bucket.Object(self._get_key(directory, file))
        file_bytes = io.BytesIO(obj.get()["Body"].read())
        return pd.read_csv(file_bytes)

    def save_csv(self, directory: S3Directory, file: str, df: pd.DataFrame) -> None:
        key = self._get_key(directory, file)
        self._s3_bucket.put_object(Key=key, Body=df.to_csv(index=False))
        logger.info(f"Successfully saved {key} to S3")

    def delete_files(self, paths: list[str]) -> None:
        if not paths:
            return
        for i in range(0, len(paths), 1000):
            chunk = paths[i:i + 1000]
            self._s3_bucket.delete_objects(Delete={"Objects": [{"Key": path} for path in chunk]})
        logger.info(f"Successfully deleted {len(paths)} files from S3")
