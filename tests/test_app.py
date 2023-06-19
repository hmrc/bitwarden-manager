import logging
import os
from unittest import mock
from unittest.mock import patch, Mock

import pytest
from _pytest.logging import LogCaptureFixture

from app import handler
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.export_vault import ExportVault


@mock.patch("boto3.client")
def test_handler_errors_on_invalid_format_events(boto_mock: Mock, caplog: LogCaptureFixture) -> None:
    with pytest.raises(KeyError):
        handler(event=dict(not_what_we="are_expecting"), context={})


@mock.patch("boto3.client")
def test_handler_ignores_unknown_events(boto_mock: Mock, caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        handler(event=dict(event_name="some_other_event"), context={})

    assert "ignoring unknown event 'some_other_event'" in caplog.text


@mock.patch("boto3.client")
def test_handler_routes_new_user_events(boto_mock: Mock) -> None:
    event = dict(event_name="new_user")
    with patch.object(OnboardUser, "run") as mock_method, mock.patch.dict(os.environ, {"ORGANISATION_ID": "abc-123"}):
        handler(event=event, context={})

    mock_method.assert_called_once_with(event=event)


@mock.patch("boto3.client")
def test_handler_routes_export_vault_events(boto_mock: Mock) -> None:
    event = dict(event_name="export_vault")
    with patch.object(ExportVault, "run") as mock_method, mock.patch.dict(os.environ, {"ORGANISATION_ID": "abc-123"}):
        handler(event=event, context={})

    mock_method.assert_called_once_with(event=event)
