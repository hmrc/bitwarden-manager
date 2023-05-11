from unittest import mock
from unittest.mock import Mock, call

from bitwarden_manager.bitwarden_manager import BitwardenManager


@mock.patch("boto3.client")
def test_get_credentails(mock_secretsmanager: Mock) -> None:
    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    manager = BitwardenManager()

    assert manager.get_ldap_username() == "secret"
    assert manager.get_ldap_password() == "secret"

    get_secret_value.assert_has_calls(
        [call(SecretId="/bitwarden/ldap-username"), call(SecretId="/bitwarden/ldap-password")]
    )
