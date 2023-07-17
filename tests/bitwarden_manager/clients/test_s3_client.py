import gzip
import json

import boto3
import pytest
from boto3_type_annotations import s3
from mock import MagicMock
from moto import mock_s3

from bitwarden_manager.clients.s3_client import S3Client


@mock_s3  # type: ignore
def test_write_file_to_s3() -> None:
    client = S3Client()

    filepath = "bw_backup_2023.json"
    file_contents = json.dumps('{"some_key": "some_data"}')
    file = gzip.compress(bytes(file_contents, "utf-8"))
    # see https://github.com/python/mypy/issues/2427
    client.file_from_path = MagicMock(return_value=file)  # type: ignore
    bucket_name = "test_bucket"
    s3 = boto3.client("s3")
    create_bucket_in_local_region(s3, bucket_name)
    client.write_file_to_s3(bucket_name, filepath)


def create_bucket_in_local_region(s3: s3.Client, bucket_name: str) -> None:
    if s3.meta.region_name == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": s3.meta.region_name})


# see https://github.com/getmoto/moto/issues/4944
@mock_s3  # type: ignore
def test_failed_write_file_to_s3() -> None:
    client = S3Client()

    filepath = "bw_backup_2023.json"
    file_contents = json.dumps('{"some_key": "some_data"}')
    file = gzip.compress(bytes(file_contents, "utf-8"))
    # see https://github.com/python/mypy/issues/2427
    client.file_from_path = MagicMock(return_value=file)  # type: ignore
    bucket_name = "test_bucket"
    with pytest.raises(Exception, match="Failed to write to S3"):
        client.write_file_to_s3(bucket_name, filepath)


def test_file_from_path() -> None:
    client = S3Client()
    with pytest.raises(Exception, match="No such file or directory"):
        filepath = "bw_backup_2023.json"
        client.file_from_path(filepath)
