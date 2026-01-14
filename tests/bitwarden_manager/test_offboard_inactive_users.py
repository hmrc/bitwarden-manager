from unittest import mock
from unittest.mock import Mock, MagicMock

import pytest
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.handlers.offboard_inactive_users import OffboardInactiveUsers
from jsonschema import ValidationError


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_valid_event(validation_mock: Mock, logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api)
    offboard_handler.get_active_users = MagicMock(return_value={"user1@example.com", "user2@example.com"})
    offboard_handler.get_all_members = MagicMock(
        return_value={"user1@example.com", "user2@example.com", "user3@example.com"})
    offboard_handler.offboard_users = MagicMock()

    event = {"inactivity_duration": 90}

    offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)
    offboard_handler.get_active_users.assert_called_once_with(90)
    offboard_handler.get_all_members.assert_called_once()
    offboard_handler.offboard_users.assert_called_once_with({"user3@example.com"})
    print(mock_logger.info.call_args_list)
    mock_logger.info.assert_any_call("Running activity audit report 90")
    mock_logger.info.assert_any_call("Fetching organization members")
    mock_logger.info.assert_any_call("Compiling list of inactive users")
    mock_logger.info.assert_any_call("Inactive users: 1")
    mock_logger.info.assert_any_call("Removing inactive users from bitwarden")


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_invalid_event(validation_mock: Mock, logger_mock: Mock) -> None:
    logger_mock.return_value = MagicMock()

    mock_api = MagicMock(spec=BitwardenPublicApi)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api)

    validation_mock.side_effect = ValidationError("Invalid input")

    event = {"invalid_key": "some_value"}

    with pytest.raises(ValidationError, match="Invalid input"):
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)
