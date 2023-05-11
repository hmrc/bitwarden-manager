import logging
from unittest import mock
from unittest.mock import patch, Mock

from _pytest.logging import LogCaptureFixture

from app import handler
from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient


@mock.patch("boto3.client")
def test_handler_logs_the_ldap_username(boto_mock: Mock, caplog: LogCaptureFixture) -> None:
    username = "the username"

    with patch.object(AwsSecretsManagerClient, "get_secret_value", return_value=username) as mock_method:
        with caplog.at_level(logging.INFO):
            handler(event={}, context={})

        mock_method.assert_called_once_with("/bitwarden/ldap-username")
        assert username in caplog.text
