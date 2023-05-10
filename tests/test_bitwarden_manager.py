from unittest.mock import Mock

from bitwarden_manager.bitwarden_manager import BitwardenManager


def test_get_credentails():
    manager = BitwardenManager()
    manager._secretsmanager = Mock(get_secret_value=Mock(return_value="secret"))

    assert manager.get_ldap_username() == "secret"
    assert manager.get_ldap_password() == "secret"

    manager._secretsmanager.assert_has_calls({})
