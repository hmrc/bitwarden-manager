import logging
import pytest

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient

@pytest.fixture
def client():
    return BitwardenVaultClient(
        logger=logging.getLogger(),
        client_id="<Insert valid cred>",
        client_secret="<Insert valid cred>",
    )

@pytest.fixture
def invalid_client():
    return BitwardenVaultClient(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

def test_failed_login(invalid_client) -> None:
    with pytest.raises(Exception, match="Failed to login"):
        invalid_client.login()

def test_failed_logout(invalid_client) -> None:
    with pytest.raises(Exception, match="Failed to logout"):
        invalid_client.logout()

def test_login(client) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"

def test_failed_unlock(client) -> None:
    with pytest.raises(Exception, match="Failed to unlock"):
        client.unlock("Incorrect password")

def test_export_without_unlock(client) -> None:
    result = client.export_vault("Encyption Pa$$w0rd")
    assert result == "Must unlock vault first"

def test_export_vault(client) -> None:
    client.unlock("<Insert password>")
    result = client.export_vault("Encyption Pa$$w0rd")
    assert result == "Placeholder"

def test_logout(client) -> None:
    result = client.logout()
    assert result == "You have logged out."
