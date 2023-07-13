from unittest import mock
from unittest.mock import Mock, call

from bitwarden_manager.bitwarden_manager import BitwardenManager


@mock.patch("boto3.client")
def test_get_ldap_credentials(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager._get_ldap_username() == "secret"
    assert manager._get_ldap_password() == "secret"

    assert get_secret_value.call_count == 2
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
    assert get_secret_value.call_count == 1
    get_secret_value.assert_has_calls([call(SecretId="/bitwarden/api-client-id")])

    assert manager._get_bitwarden_client_secret() == "secret"
    assert get_secret_value.call_count == 2
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
    assert get_secret_value.call_count == 1
    get_secret_value.assert_has_calls([call(SecretId="/bitwarden/vault-client-id")])

    assert manager._get_bitwarden_vault_client_secret() == "secret"
    assert get_secret_value.call_count == 2

    assert manager._get_bitwarden_vault_password() == "secret"
    assert get_secret_value.call_count == 3

    assert manager._get_bitwarden_export_encryption_password() == "secret"
    assert get_secret_value.call_count == 4

    get_secret_value.assert_has_calls(
        [
            call(SecretId="/bitwarden/vault-client-id"),
            call(SecretId="/bitwarden/vault-client-secret"),
            call(SecretId="/bitwarden/vault-password"),
            call(SecretId="/bitwarden/export-encryption-password"),
        ]
    )
