import os
import pathlib
import boto3
import gzip
import json
import logging
import pytest
import re

from _pytest.logging import LogCaptureFixture
from mock import MagicMock, mock
from moto import mock_s3
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


@pytest.fixture
def client() -> BitwardenVaultClient:
    with mock.patch.dict(os.environ, {"ORGANISATION_ID": "abc-123"}):
        return BitwardenVaultClient(
            logger=logging.getLogger(),
            client_id="test_id",
            client_secret="test_secret",
            password="very secure pa$$w0rd!",
            export_enc_password="hmrc2023",
            cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./bitwarden_client_stub.py")),
        )


@pytest.fixture
def failing_client() -> BitwardenVaultClient:
    with mock.patch.dict(os.environ, {"ORGANISATION_ID": "abc-123"}):
        return BitwardenVaultClient(
            logger=logging.getLogger(),
            client_id="test_id",
            client_secret="test_secret",
            password="very secure pa$$w0rd!",
            export_enc_password="hmrc2023",
            cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./bitwarden_client_stub_failing.py")),
        )


def test_failed_login(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to login"):
        failing_client.login()


def test_export_without_unlock(client: BitwardenVaultClient) -> None:
    result = client.export_vault()
    pattern = re.compile("/tmp/bw_backup_.*.json")
    assert pattern.match(result)


def test_failed_unlock(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to unlock"):
        failing_client.unlock()


def test_logout(client: BitwardenVaultClient) -> None:
    result = client.logout()
    assert result == "You have logged out."


def test_failed_logout(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="Failed to logout"):
        failing_client.logout()


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


def test_login(client: BitwardenVaultClient) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_file_from_path(client: BitwardenVaultClient) -> None:
    with pytest.raises(Exception, match="No such file or directory"):
        filepath = "bw_backup_2023.json"
        client.file_from_path(filepath)


def test_create_collection(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Team Name None"]
    existing_collections = {"Non Matching Collection": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert f"Created {teams[0]} successfully" in caplog.text


def test_create_collection_unlocked(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    client.unlock()
    client.login()
    teams = ["Team Name None"]
    existing_collections = {"Team Name One": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    client.create_collection(teams, existing_collections)
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert f"Created {teams[0]} successfully" in caplog.text


def test_no_missing_collections(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Existing Collection Name"]
    existing_collections = {"Existing Collection Name": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert "No missing collections found" in caplog.text
