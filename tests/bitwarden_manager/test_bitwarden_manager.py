import logging
import os
from unittest import mock
from unittest.mock import Mock, call, patch

from pytest import LogCaptureFixture
import pytest


from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.confirm_user import BitwardenConfirmUserInvalidDomain


@mock.patch("boto3.client")
def test_get_secret(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager._get_secret("ldap-username") == "secret"
    assert manager._get_secret("ldap-password") == "secret"

    assert get_secret_value.call_count == 3
    get_secret_value.assert_has_calls(
        [
            #  must be in order called
            call(SecretId="/bitwarden/export-encryption-password"),  # called in bw manager init
            call(SecretId="/bitwarden/ldap-username"),
            call(SecretId="/bitwarden/ldap-password"),
        ]
    )


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": "example.com"})
@mock.patch("boto3.client")
def test_confirm_user_passed_allowed_domains(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    bitwarden_mock = Mock(
        spec=BitwardenVaultClient,
        list_unconfirmed_users=Mock(return_value=[dict(email="test@example.com", id=111)]),
    )

    with patch.object(BitwardenManager, "_get_bitwarden_vault_client") as _get_bitwarden_vault_client:
        _get_bitwarden_vault_client.return_value = bitwarden_mock
        BitwardenManager().run(event={"event_name": "confirm_user"})

    bitwarden_mock.confirm_user.assert_called_once_with(user_id=111)


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": "example.com"})
@mock.patch("boto3.client")
def test_confirm_user_failed_when_passed_users_with_invalid_email_domains(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    bitwarden_mock = Mock(
        spec=BitwardenVaultClient,
        list_unconfirmed_users=Mock(
            return_value=[dict(email="test@example.com", id=111), dict(email="test@evil.com", id=222)]
        ),
    )

    with patch.object(BitwardenManager, "_get_bitwarden_vault_client") as _get_bitwarden_vault_client:
        _get_bitwarden_vault_client.return_value = bitwarden_mock
        with pytest.raises(ExceptionGroup, match="User Confirmation Errors: ") as exception_group:
            BitwardenManager().run(event={"event_name": "confirm_user"})
            assert exception_group.group_contains(
                BitwardenConfirmUserInvalidDomain, match="Invalid Domain detected: evil.com"
            )

    bitwarden_mock.confirm_user.assert_called_once_with(user_id=111)


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": "example.com"})
@mock.patch("boto3.client")
def test_warning_is_logged_on_failed_bitwarden_vault_client_login(
    mock_secretsmanager: Mock, failing_authentication_client: BitwardenVaultClient, caplog: LogCaptureFixture
) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    with patch.object(BitwardenManager, "_get_bitwarden_vault_client") as _get_bitwarden_vault_client:
        _get_bitwarden_vault_client.return_value = failing_authentication_client

        with caplog.at_level(logging.WARN):
            BitwardenManager().run(event={"event_name": "confirm_user"})

        assert "Failed to complete confirm_user due to Bitwarden CLI login error - " in caplog.text


@mock.patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
@mock.patch("boto3.client")
def test_event_is_logged_in_debug_mode(
    mock_secretsmanager: Mock, failing_authentication_client: BitwardenVaultClient, caplog: LogCaptureFixture
) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    bitwarden_mock = Mock(
        spec=BitwardenVaultClient,
        list_unconfirmed_users=Mock(
            return_value=[dict(email="test@example.com", id=111), dict(email="test@evil.com", id=222)]
        ),
    )
    with patch.object(BitwardenManager, "_get_bitwarden_vault_client") as _get_bitwarden_vault_client:
        _get_bitwarden_vault_client.return_value = bitwarden_mock

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ExceptionGroup, match="User Confirmation Errors: ") as exception_group:
                BitwardenManager().run(event={"event_name": "confirm_user"})
                assert exception_group.group_contains(
                    BitwardenConfirmUserInvalidDomain, match="Invalid Domain detected: evil.com"
                )

            assert "{'event_name': 'confirm_user'}" in caplog.text


@mock.patch("boto3.client")
def test_get_allowed_domains_returns_empty_list_of_domains(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    assert BitwardenManager()._get_allowed_email_domains() == []


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": "example.com,foo.com"})
@mock.patch("boto3.client")
def test_get_allowed_domains_retuns_list_of_domains_from_string(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    assert BitwardenManager()._get_allowed_email_domains() == ["example.com", "foo.com"]


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": " example.com, foo.com  "})
@mock.patch("boto3.client")
def test_get_allowed_domains_handles_whitespace(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    assert BitwardenManager()._get_allowed_email_domains() == ["example.com", "foo.com"]


@mock.patch.dict(os.environ, {"BITWARDEN_CLI_TIMEOUT": "25"})
@mock.patch("boto3.client")
def test_bw_cli_timeout(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    assert BitwardenManager()._get_bitwarden_cli_timeout() == 25.0


@mock.patch.dict(os.environ, {"BITWARDEN_CLI_TIMEOUT": "text"})
@mock.patch("boto3.client")
def test_invalid_bw_cli_timeout(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)

    assert BitwardenManager()._get_bitwarden_cli_timeout() == 20.0
