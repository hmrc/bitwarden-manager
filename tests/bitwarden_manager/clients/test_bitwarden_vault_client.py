import pathlib
import logging
import pytest
import re

from _pytest.logging import LogCaptureFixture
from bitwarden_manager.clients.bitwarden_vault_client import (
    BitwardenVaultClient,
    BitwardenVaultClientError,
)


@pytest.fixture
def client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./bitwarden_client_stub.py")),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
    )


@pytest.fixture
def failing_client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(
            pathlib.Path(__file__).parent.joinpath("./bitwarden_client_stub_failing_operations.py")
        ),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
    )


@pytest.fixture
def failing_authentication_client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(
            pathlib.Path(__file__).parent.joinpath("./bitwarden_client_stub_failing_authentication.py")
        ),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
    )


def test_failed_login(failing_authentication_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="login"):
        failing_authentication_client.login()


def test_export(client: BitwardenVaultClient) -> None:
    result = client.export_vault()
    pattern = re.compile("/tmp/bw_backup_.*.json")
    assert pattern.match(result)


def test_export_fails(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(
        BitwardenVaultClientError, match="Redacting stack trace information for export to avoid logging password"
    ):
        failing_client.export_vault()


def test_failed_unlock(failing_authentication_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="unlock"):
        failing_authentication_client.unlock()


def test_logout(client: BitwardenVaultClient) -> None:
    result = client.logout()
    assert result == "You have logged out."


def test_failed_logout(failing_authentication_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="logout"):
        failing_authentication_client.logout()


def test_login(client: BitwardenVaultClient) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_create_collection(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Team Name"]
    existing_collections = {"Non Matching Collection": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with caplog.at_level(logging.INFO):
        client.create_collection(teams, existing_collections)
    assert f"Created {teams[0]} successfully" in caplog.text


def test_create_collection_fails(failing_client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    teams = ["Team Name"]
    existing_collections = {"Non Matching Collection": "YYYYYYYY-YYYY-YYYY-YYYY-YYYYYYYYYYYY"}
    with pytest.raises(BitwardenVaultClientError, match="create', 'org-collection'"):
        failing_client.create_collection(teams, existing_collections)


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
