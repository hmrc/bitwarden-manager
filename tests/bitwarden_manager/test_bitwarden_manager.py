import os
from unittest import mock
from unittest.mock import Mock, call, patch


from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


@mock.patch("boto3.client")
def test_get_ldap_credentials(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager._get_ldap_username() == "secret"
    assert manager._get_ldap_password() == "secret"

    assert get_secret_value.call_count == 3
    get_secret_value.assert_has_calls(
        [
            call(SecretId="/bitwarden/ldap-username"),
            call(SecretId="/bitwarden/ldap-password"),
        ]
    )


@mock.patch("boto3.client")
def test_get_bitwarden_api_creds(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager._get_bitwarden_client_id() == "secret"
    get_secret_value.assert_has_calls([call(SecretId="/bitwarden/api-client-id")])

    assert manager._get_bitwarden_client_secret() == "secret"
    get_secret_value.assert_has_calls(
        [
            call(SecretId="/bitwarden/api-client-id"),
            call(SecretId="/bitwarden/api-client-secret"),
        ]
    )


@mock.patch("boto3.client")
def test_get_bitwarden_vault_creds(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager._get_bitwarden_vault_client_id() == "secret"
    get_secret_value.assert_has_calls([call(SecretId="/bitwarden/vault-client-id")])

    assert manager._get_bitwarden_vault_client_secret() == "secret"
    assert manager._get_bitwarden_vault_password() == "secret"
    assert manager._get_bitwarden_export_encryption_password() == "secret"

    get_secret_value.assert_has_calls(
        [
            call(SecretId="/bitwarden/vault-client-id"),
            call(SecretId="/bitwarden/vault-client-secret"),
            call(SecretId="/bitwarden/vault-password"),
            call(SecretId="/bitwarden/export-encryption-password"),
        ]
    )


@mock.patch.dict(os.environ, {"ALLOWED_DOMAINS": "example.com"})
@mock.patch("boto3.client")
def test_confirm_user_passed_allowed_domains(mock_secretsmanager: Mock) -> None:
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

        manager = BitwardenManager()
        manager.run(event={"event_name": "confirm_user"})

    bitwarden_mock.confirm_user.assert_called_once_with(user_id=111)


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
