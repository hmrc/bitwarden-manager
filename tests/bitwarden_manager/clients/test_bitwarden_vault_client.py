import os
import logging
import tempfile
import subprocess  # nosec B404

from unittest import mock
from unittest.mock import patch

import pytest

from _pytest.logging import LogCaptureFixture
from bitwarden_manager.clients.bitwarden_vault_client import (
    BitwardenVaultClient,
    BitwardenVaultClientError,
    BitwardenVaultClientIncorrectCredentialsError,
    BitwardenVaultClientLoginError,
)


def test_failed_login(incorrect_credentials_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientIncorrectCredentialsError, match="login"):
        incorrect_credentials_client.login()


def test_only_logout_if_logged_in(failing_authentication_client: BitwardenVaultClient) -> None:
    failing_authentication_client.logout()


@mock.patch.dict(os.environ, {"BITWARDEN_CLI_TIMEOUT": "1"})
def test_login_timed_out(timeout_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientLoginError, match="timed out after 1.0 seconds"):
        timeout_client.login()


def check_cli_server() -> str:
    tmp_env = os.environ.copy()
    tmp_env["BITWARDENCLI_APPDATA_DIR"] = "/tmp/.config"  # nosec B108
    output = subprocess.check_output(
        ["bw", "config", "server"],
        env=tmp_env,
        shell=False,
        stderr=subprocess.PIPE,
        timeout=20,
        text=True,
    )  # nosec B603
    return output


def test_configure_server() -> None:
    client = BitwardenVaultClient(
        cli_executable_path="bw",
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=20,
    )
    client.configure_server()
    result = check_cli_server()
    assert result == "https://vault.bitwarden.eu"


def test_configure_server_fails(failing_config_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError):
        failing_config_client.configure_server()


def test_login(client: BitwardenVaultClient) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


def test_export(client: BitwardenVaultClient) -> None:
    with tempfile.NamedTemporaryFile() as tmpfile:
        client.export_vault(file_path=tmpfile.name)
        file_content = tmpfile.readlines()
    assert b'{"test": "foo"}' in file_content


def test_export_fails(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(
        BitwardenVaultClientError, match="Redacting stack trace information for export to avoid logging password"
    ):
        failing_client.export_vault(file_path="foo")


def test_unlock(client: BitwardenVaultClient) -> None:
    assert client._unlock() == "thisisatoken"


def test_session_token_remembers_token(client: BitwardenVaultClient) -> None:
    with patch.object(BitwardenVaultClient, "_unlock") as unlock_mock:
        client.session_token()
        client.session_token()

    unlock_mock.assert_called_once()


def test_failed_unlock(failing_authentication_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="unlock"):
        failing_authentication_client._unlock()


def test_logout(client: BitwardenVaultClient) -> None:
    client.authenticate()
    assert client._BitwardenVaultClient__session_token  # type: ignore
    client.logout()
    assert client._BitwardenVaultClient__session_token is None  # type: ignore


def test_failed_logout(failing_authentication_client: BitwardenVaultClient) -> None:
    # pretending we're logged in
    failing_authentication_client._BitwardenVaultClient__session_token = "foo"  # type: ignore
    with pytest.raises(BitwardenVaultClientError, match="logout"):
        failing_authentication_client.logout()


def test_create_collections(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    missing_collection_names = ["Team Name"]
    with caplog.at_level(logging.INFO):
        client.create_collections(missing_collection_names)
    assert f"Created collection: {missing_collection_names[0]}" in caplog.text


def test_create_collections_fails(failing_client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    missing_collection_names = ["Team Name"]
    with pytest.raises(BitwardenVaultClientError, match="create', 'org-collection'"):
        failing_client.create_collections(missing_collection_names)


def test_create_collections_unlocked(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    client._unlock()
    client.login()
    missing_collection_names = ["Team Name"]
    with caplog.at_level(logging.INFO):
        client.create_collections(missing_collection_names)
    assert f"Created collection: {missing_collection_names[0]}" in caplog.text


def test_list_org_users(client: BitwardenVaultClient) -> None:
    unconfirmed_users = client.list_unconfirmed_users()
    assert isinstance(unconfirmed_users, list)
    assert isinstance(unconfirmed_users[0], dict)
    assert isinstance(unconfirmed_users[0]["id"], str)
    assert isinstance(unconfirmed_users[0]["email"], str)


def test_list_org_users_failed(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="'list', 'org-members'"):
        failing_client.list_unconfirmed_users()


def test_confirm_user(client: BitwardenVaultClient, caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        client.confirm_user(user_id="example_id")
    assert "User example_id confirmed successfully" in caplog.text


def test_confirm_user_failed_to_parse(failing_client: BitwardenVaultClient) -> None:
    with pytest.raises(BitwardenVaultClientError, match="'confirm', 'org-member'"):
        failing_client.confirm_user(user_id="example_id")
