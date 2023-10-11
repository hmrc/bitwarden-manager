import logging
from unittest import mock
from unittest.mock import patch, Mock, MagicMock

import pytest
from _pytest.logging import LogCaptureFixture

from app import handler
from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from bitwarden_manager.offboard_user import OffboardUser
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.export_vault import ExportVault
from bitwarden_manager.confirm_user import ConfirmUser


@mock.patch("boto3.client")
def test_handler_errors_on_invalid_format_events(_: Mock, caplog: LogCaptureFixture) -> None:
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        with pytest.raises(KeyError):
            handler(event=dict(not_what_we="are_expecting"), context={})


@mock.patch("boto3.client")
@mock.patch("bitwarden_manager.clients.bitwarden_vault_client.BitwardenVaultClient")
def test_handler_ignores_unknown_events(_: Mock, __: Mock, caplog: LogCaptureFixture) -> None:
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        with patch.object(BitwardenVaultClient, "logout"):
            with caplog.at_level(logging.INFO):
                handler(event=dict(event_name="some_other_event"), context={})

    assert "ignoring unknown event 'some_other_event'" in caplog.text


@mock.patch("boto3.client")
def test_bitwarden_client_logout_is_called(_: Mock) -> None:
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        with patch.object(BitwardenVaultClient, "logout") as bitwarden_logout:
            handler(event=dict(event_name="some_ot23her_event"), context={})

    bitwarden_logout.assert_called_once()


@mock.patch("boto3.client")
def test_bitwarden_client_logout_is_called_even_when_exception_thrown(_: Mock) -> None:
    with patch.object(BitwardenVaultClient, "logout") as bitwarden_logout:
        with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
            secrets_manager_mock.return_value = "23497858247589473589734805734853"
            event = dict(event_name="new_user")
            with patch.object(OnboardUser, "run", MagicMock(side_effect=BitwardenVaultClientError())) as new_user_mock:
                with pytest.raises(BitwardenVaultClientError):
                    handler(event=event, context={})

    new_user_mock.assert_called_once_with(event=event)
    bitwarden_logout.assert_called_once()


@mock.patch("boto3.client")
def test_handler_routes_new_user_events(_: Mock) -> None:
    with patch.object(BitwardenVaultClient, "logout"):
        with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
            secrets_manager_mock.return_value = "23497858247589473589734805734853"
            event = dict(event_name="new_user")
            with patch.object(OnboardUser, "run") as new_user_mock:
                handler(event=event, context={})

    new_user_mock.assert_called_once_with(event=event)


@mock.patch("boto3.client")
def test_handler_routes_export_vault_events(_: Mock) -> None:
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        event = dict(event_name="export_vault")
        with patch.object(BitwardenVaultClient, "logout") as bitwarden_logout:
            with patch.object(ExportVault, "run") as export_vault_mock:
                handler(event=event, context={})

    export_vault_mock.assert_called_once_with(event=event)
    bitwarden_logout.assert_called_once()


@mock.patch("boto3.client")
def test_handler_routes_confirm_user(_: Mock) -> None:
    event = dict(event_name="confirm_user")
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        with patch.object(BitwardenVaultClient, "logout") as bitwarden_logout:
            with patch.object(ConfirmUser, "run") as confirm_user_mock:
                handler(event=event, context={})

    confirm_user_mock.assert_called_once_with(event=event)
    bitwarden_logout.assert_called_once()


@mock.patch("boto3.client")
def test_handler_routes_remove_user(_: Mock) -> None:
    event = dict(event_name="remove_user")
    with patch.object(AwsSecretsManagerClient, "get_secret_value") as secrets_manager_mock:
        secrets_manager_mock.return_value = "23497858247589473589734805734853"
        with patch.object(BitwardenVaultClient, "logout") as bitwarden_logout:
            with patch.object(OffboardUser, "run") as remove_user_mock:
                handler(event=event, context={})

    remove_user_mock.assert_called_once_with(event=event)
    bitwarden_logout.assert_called_once()
