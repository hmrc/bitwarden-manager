import pytest
from botocore.exceptions import BotoCoreError

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient

from unittest.mock import Mock


def test_get_secret_value_username() -> None:
    secretsmanager_client = Mock(get_secret_value=Mock(return_value={"SecretString": "some-secret-value"}))
    client = AwsSecretsManagerClient(secretsmanager_client=secretsmanager_client)
    expected = "some-secret-value"
    got = client.get_secret_value("/bitwarden/username")

    assert got == expected


def test_get_secret_value_failure() -> None:
    secretsmanager_client = Mock(get_secret_value=Mock(side_effect=BotoCoreError()))
    client = AwsSecretsManagerClient(secretsmanager_client=secretsmanager_client)

    with pytest.raises(Exception, match="failed to fetch secret value from id: '/bitwarden/username'"):
        client.get_secret_value("/bitwarden/username")
