from unittest import mock
from unittest.mock import Mock, MagicMock, patch

import pytest
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.handlers.offboard_inactive_users import OffboardInactiveUsers
from jsonschema import ValidationError

GET_MEMBERS_DICT = [
    {
        "object": "member",
        "id": None,
        "userId": "11111111",
        "name": "test user01",
        "email": "test.user01@example.com",
        "twoFactorEnabled": False,
        "status": 2,
        "collections": None,
        "type": 1,
        "accessAll": False,
        "externalId": "test.user01",
        "resetPasswordEnrolled": False,
        "permissions": None,
    },
    {
        "object": "member",
        "id": None,
        "userId": "22222222",
        "name": "test user02",
        "email": "test.user02@example.com",
        "twoFactorEnabled": True,
        "status": 2,
        "collections": [
            {"id": "id-manager-created", "readOnly": True, "hidePasswords": False, "manage": False},
            {"id": "id-manually-created", "readOnly": False, "hidePasswords": False, "manage": True},
        ],
        "type": 2,
        "accessAll": False,
        "externalId": "test.user02",
        "resetPasswordEnrolled": False,
        "permissions": None,
    },
    {
        "object": "member",
        "id": None,
        "userId": "33333333",
        "name": "test user03",
        "email": "test.user03@example.com",
        "twoFactorEnabled": True,
        "status": 0,
        "collections": None,
        "type": 1,
        "accessAll": False,
        "externalId": None,
        "resetPasswordEnrolled": False,
        "permissions": None,
    },
]


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_valid_event(validation_mock: Mock, logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client)
    mock_api.get_active_user_report = MagicMock(return_value={"11111111", "22222222", "77777777"})
    mock_api.get_users = MagicMock(return_value=GET_MEMBERS_DICT)
    all_users = {
        "11111111": "test.user01@example.com",
        "22222222": "test.user02@example.com",
        "33333333": "test.user03@example.com",
    }

    event = {"event_name": "offboard_inactive_users", "inactivity_duration": 90}

    with (
        patch.object(offboard_handler, "offboard_users") as mock_offboard_users,
        patch.object(offboard_handler, "_get_protected_users") as mock_protected_users,
    ):
        mock_protected_users.return_value = set()
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)
    mock_api.get_active_user_report.assert_called_once_with(90)
    mock_api.get_users.assert_called_once()
    mock_offboard_users.assert_called_once_with({"33333333"}, all_users, set())
    mock_logger.info.assert_any_call("Compiling list of active users for the last 90 days")
    mock_logger.info.assert_any_call("Fetching organization members")
    mock_logger.info.assert_any_call("Compiling list of inactive users")
    mock_logger.info.assert_any_call("Inactive users: 1")
    mock_logger.info.assert_any_call("Compiling list of protected users")
    mock_logger.info.assert_any_call("Removing inactive users from bitwarden")


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_invalid_event(validation_mock: Mock, logger_mock: Mock) -> None:
    logger_mock.return_value = MagicMock()

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client)

    validation_mock.side_effect = ValidationError("Invalid input")

    event = {"invalid_key": "some_value"}

    with pytest.raises(ValidationError, match="Invalid input"):
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)
