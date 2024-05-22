from typing import IO

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class S3Client:
    def __init__(self) -> None:
        self._boto_s3 = boto3.client("s3")

    def write_file_to_s3(self, bucket_name: str, filepath: str, filename: str) -> None:
        try:
            self._boto_s3.put_object(Bucket=bucket_name, Key=filename, Body=self.file_from_path(filepath))
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to write to S3", e) from e

    def read_object(self, bucket_name: str, key: str) -> str:
        try:
            data = self._boto_s3.get_object(Bucket=bucket_name, Key=key)
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Failed to read s3://{bucket_name}/{key}", e) from e
        return str(data["Body"].read().decode("utf-8"))

    def file_from_path(self, filepath: str) -> IO[bytes]:
        return open(filepath, "rb")
