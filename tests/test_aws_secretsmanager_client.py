from bitwarden_manager.aws_secretsmanager_client import AwsSecretsManagerClient

from unittest.mock import Mock


def test_get_secret_value() -> None:
    client = AwsSecretsManagerClient()
    client._secretsmanager = Mock(get_secret_value=Mock(return_value={"SecretString": "some-secret-value"}))
    expected = "some-secret-value"
    got = client.get_secret_value("/bitwarden/username")

    assert got == expected
