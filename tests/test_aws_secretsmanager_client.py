import pytest
from botocore.exceptions import BotoCoreError

from bitwarden_manager.aws_secretsmanager_client import AwsSecretsManagerClient

from unittest.mock import Mock


def test_get_secret_value_username() -> None:
    client = AwsSecretsManagerClient()
    client._secretsmanager = Mock(get_secret_value=Mock(return_value={"SecretString": "some-secret-value"}))
    expected = "some-secret-value"
    got = client.get_secret_value("/bitwarden/username")

    assert got == expected


def test_get_secret_value_failure() -> None:
    client = AwsSecretsManagerClient()
    client._secretsmanager = Mock(get_secret_value=Mock(side_effect=BotoCoreError()))

    with pytest.raises(Exception, match="failed to fetch secret value from id: '/bitwarden/username'"):
        client.get_secret_value("/bitwarden/username")
