import os

import boto3
import gzip
import json
import logging
import pytest
import re

from _pytest.logging import LogCaptureFixture
from mock import MagicMock, mock
from moto import mock_s3
from typing import Optional
from typing import Self
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


class MockedPopen:
    def __init__(self, args: str, **kwargs: str) -> None:
        self.args = args
        self.returncode = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: str, value: str, traceback: str) -> None:
        pass

    def communicate(self, input: Optional[str] = None, timeout: Optional[int] = None) -> tuple[bytes, bytes]:
        if self.args[0] == "./bw" and self.args[1] == "login":
            stdout = b"You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"
            stderr = b""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "logout":
            stdout = b"You have logged out."
            stderr = b""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "unlock":
            stdout = b"Unlocked"
            stderr = b""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "export":
            stdout = b""
            stderr = b""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "create":
            stdout = b"Collection successfully created"
            stderr = b""
            self.returncode = 0
        else:
            stdout = b""
            stderr = b"unknown command"
            self.returncode = 1
        return stdout, stderr


class FailedMockedPopen:
    def __init__(self, args: str, **kwargs: str) -> None:
        self.args = args
        self.returncode = 1

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: str, value: str, traceback: str) -> None:
        pass

    def communicate(self, input: Optional[str] = None, timeout: Optional[int] = None) -> tuple[bytes, bytes]:
        stdout = b""
        stderr = b"Command failed"
        self.returncode = 1
        return stdout, stderr


@pytest.fixture
def client() -> BitwardenVaultClient:
    with mock.patch.dict(os.environ, {"ORGANISATION_ID": "abc-123"}):
        return BitwardenVaultClient(
            logger=logging.getLogger(),
            client_id="test_id",
            client_secret="test_secret",
            password="very secure pa$$w0rd!",
            export_enc_password="hmrc2023",
        )


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_login(client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to login"):
        client.login()


@mock.patch("subprocess.Popen", MockedPopen)
def test_export_without_unlock(client: BitwardenVaultClient) -> None:
    result = client.export_vault()
    pattern = re.compile("/tmp/bw_backup_.*.json")
    assert pattern.match(result)


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_unlock(client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to unlock"):
        client.unlock()


@mock.patch("subprocess.Popen", MockedPopen)
def test_logout(client: BitwardenVaultClient) -> None:
    result = client.logout()
    assert result == "You have logged out."


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_logout(client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to logout"):
        client.logout()


@mock_s3  # type: ignore
def test_write_file_to_s3(client: BitwardenVaultClient) -> None:
    filepath = "bw_backup_2023.json"
    file_contents = json.dumps('{"some_key": "some_data"}')
    file = gzip.compress(bytes(file_contents, "utf-8"))
    # see https://github.com/python/mypy/issues/2427
    client.file_from_path = MagicMock(return_value=file)  # type: ignore
    bucket_name = "test_bucket"
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    client.write_file_to_s3(bucket_name, filepath)


# see https://github.com/getmoto/moto/issues/4944
@mock_s3  # type: ignore
def test_failed_write_file_to_s3(client: BitwardenVaultClient) -> None:
    filepath = "bw_backup_2023.json"
    file_contents = json.dumps('{"some_key": "some_data"}')
    file = gzip.compress(bytes(file_contents, "utf-8"))
    # see https://github.com/python/mypy/issues/2427
    client.file_from_path = MagicMock(return_value=file)  # type: ignore
    bucket_name = "test_bucket"
    with pytest.raises(Exception, match="Failed to write to S3"):
        client.write_file_to_s3(bucket_name, filepath)


@mock.patch("subprocess.Popen", MockedPopen)
def test_login(client: BitwardenVaultClient) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_file_from_path(client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="No such file or directory"):
        filepath = "bw_backup_2023.json"
        client.file_from_path(filepath)


@mock.patch("subprocess.Popen", MockedPopen)
def test_create_collection(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Team Name None"]
    existing_collections = {"Non Matching Collection": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert f"Created {teams[0]} successfully" in caplog.text


@mock.patch("subprocess.Popen", MockedPopen)
def test_create_collection_unlocked(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    client.unlock()
    client.login()
    teams = ["Team Name None"]
    existing_collections = {"Team Name One": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    client.create_collection(teams, existing_collections)
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert f"Created {teams[0]} successfully" in caplog.text


@mock.patch("subprocess.Popen", MockedPopen)
def test_no_missing_collections(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Existing Collection Name"]
    existing_collections = {"Existing Collection Name": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert "No missing collections found" in caplog.text
