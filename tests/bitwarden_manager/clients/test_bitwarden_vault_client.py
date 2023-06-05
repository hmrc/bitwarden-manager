import logging
import pytest
import mock

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


class MockedPopen:
    def __init__(self, args, **kwargs):
        self.args = args
        self.returncode = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        pass

    def communicate(self, input=None, timeout=None):
        if self.args[0] == "./bw" and self.args[1] == "login":
            stdout = b"You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"
            stderr = ""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "logout":
            stdout = b"You have logged out."
            stderr = ""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "unlock":
            stdout = b"Unlocked"
            stderr = ""
            self.returncode = 0
        elif self.args[0] == "./bw" and self.args[1] == "export":
            stdout = b"Placeholder"
            stderr = ""
            self.returncode = 0
        else:
            stdout = ""
            stderr = b"unknown command"
            self.returncode = 1
        return stdout, stderr


class FailedMockedPopen:
    def __init__(self, args, **kwargs):
        self.args = args
        self.returncode = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        pass

    def communicate(self, input=None, timeout=None):
        stdout = ""
        stderr = b"Command failed"
        self.returncode = 1
        return stdout, stderr


@pytest.fixture
def client():
    return BitwardenVaultClient(
        logger=logging.getLogger(), client_id="test_id", client_secret="test_secret", password="very secure pa$$w0rd!"
    )


@mock.patch("subprocess.Popen", MockedPopen)
def test_login(client) -> None:
    result = client.login()
    assert result == "You are logged in!\n\nTo unlock your vault, use the `unlock` command. ex:\n$ bw unlock"


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_login(client) -> None:
    with pytest.raises(Exception, match="Failed to login"):
        client.login()


@mock.patch("subprocess.Popen", MockedPopen)
def test_export_without_unlock(client) -> None:
    result = client.export_vault("Encyption Pa$$w0rd")
    assert result == "Must unlock vault first"


@mock.patch("subprocess.Popen", MockedPopen)
def test_export_vault(client) -> None:
    client.unlock()
    result = client.export_vault("Encyption Pa$$w0rd")
    assert result == "Placeholder"


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_unlock(client) -> None:
    with pytest.raises(Exception, match="Failed to unlock"):
        client.unlock()


@mock.patch("subprocess.Popen", MockedPopen)
def test_logout(client) -> None:
    result = client.logout()
    assert result == "You have logged out."


@mock.patch("subprocess.Popen", FailedMockedPopen)
def test_failed_logout(client) -> None:
    with pytest.raises(Exception, match="Failed to logout"):
        client.logout()
