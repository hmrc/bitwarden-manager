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
        "id": "11111111",
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
        "id": "22222222",
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
        "id": "33333333",
        "userId": "33333333",
        "name": "test user03",
        "email": "test.user03@example.com",
        "twoFactorEnabled": True,
        "status": 2,
        "collections": None,
        "type": 1,
        "accessAll": False,
        "externalId": None,
        "resetPasswordEnrolled": False,
        "permissions": None,
    },
    {
        "object": "member",
        "id": "44444444",
        "userId": "44444444",
        "name": "test user04",
        "email": "test.user04@example.com",
        "twoFactorEnabled": True,
        "status": 2,
        "collections": None,
        "type": 1,
        "accessAll": False,
        "externalId": None,
        "resetPasswordEnrolled": False,
        "permissions": None,
    },
]

GET_EVENTS_LIST = [
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfad",
        "memberId": "11111111",
        "actingUserId": None,
    },
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfaf",
        "memberId": None,
        "actingUserId": "11111111",
    },
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfaf",
        "memberId": "22222222",
        "actingUserId": None,
    },
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfaf",
        "memberId": None,
        "actingUserId": "22222222",
    },
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfaf",
        "memberId": "33333333",
        "actingUserId": None,
    },
    {
        "object": "event",
        "type": 1000,
        "itemId": "3767a302-8208-4dc6-b842-030428a1cfaf",
        "memberId": None,
        "actingUserId": "33333333",
    },
]


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_valid_event(validation_mock: Mock, logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    mock_api.get_users = MagicMock(return_value=GET_MEMBERS_DICT)
    mock_api.get_events = Mock(return_value=GET_EVENTS_LIST)

    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client)

    expected_inactive = {"44444444"}

    expected_members = {
        "11111111": "test.user01@example.com",
        "22222222": "test.user02@example.com",
        "33333333": "test.user03@example.com",
        "44444444": "test.user04@example.com",
    }

    event = {"event_name": "offboard_inactive_users", "inactivity_duration": 90}

    with (
        patch.object(offboard_handler, "offboard_users") as mock_offboard_users,
        patch.object(offboard_handler, "_get_protected_users") as mock_protected_users,
    ):
        mock_protected_users.return_value = set()
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)
    mock_api.get_users.assert_called_once()
    mock_api.get_events.assert_called_once()
    mock_logger.info.assert_any_call("Compiling list of active members for the last 90 days")
    mock_logger.info.assert_any_call("Fetching organization members")
    mock_logger.info.assert_any_call("Compiling list of inactive members")
    mock_logger.info.assert_any_call("Compiling list of protected members")
    mock_logger.info.assert_any_call("Total members: 4, Active members: 3, Inactive members: 1")
    mock_logger.info.assert_any_call("Removing 1 inactive members from bitwarden")
    mock_offboard_users.assert_called_once_with(expected_inactive, expected_members, set())


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_null_events(validation_mock: Mock, logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    mock_api.get_users = MagicMock(return_value=GET_MEMBERS_DICT)
    mock_api.get_events = Mock(return_value=None)

    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client)
    event = {"event_name": "offboard_inactive_users", "inactivity_duration": 90}

    with pytest.raises(ValueError, match="The current list of events must be provided"):
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.validate")
def test_run_null_members(validation_mock: Mock, logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    mock_api.get_users = MagicMock(return_value=None)
    mock_api.get_events = Mock(return_value=GET_EVENTS_LIST)

    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client)
    event = {"event_name": "offboard_inactive_users", "inactivity_duration": 90}

    with pytest.raises(ValueError, match="The current list of active members must be provided"):
        offboard_handler.run(event)

    validation_mock.assert_called_once_with(instance=event, schema=mock.ANY)


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
