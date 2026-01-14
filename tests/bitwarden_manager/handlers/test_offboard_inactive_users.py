from unittest import mock
from unittest.mock import Mock, MagicMock

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.handlers.offboard_inactive_users import OffboardInactiveUsers


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_offboard_users(logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api)

    inactive_users = {"user1@example.com", "user2@example.com"}
    offboard_handler.offboard_users(inactive_users)

    mock_logger.info.assert_any_call("Removing user user1@example.com from bitwarden")
    mock_logger.info.assert_any_call("Removing user user2@example.com from bitwarden")


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_get_all_members(logger_mock: Mock):
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_api.get_users.return_value = [
        {
            "object": "member",
            "id": "11111111",
            "userId": None,
            "name": "test user01",
            "email": "test.user01@example.com",
            "twoFactorEnabled": False,
            "status": 2,
            "collections": None,
            "type": 1,
            "accessAll": False,
            "externalId": "test.user01",
            "resetPasswordEnrolled": False,
            "permissions": None
        },
        {
            "object": "member",
            "id": "22222222",
            "userId": None,
            "name": "test user02",
            "email": "test.user02@example.com",
            "twoFactorEnabled": True,
            "status": 2,
            "collections": [{
                "id": "id-manager-created",
                "readOnly": True,
                "hidePasswords": False,
                "manage": False
            },
                {
                    "id": "id-manually-created",
                    "readOnly": False,
                    "hidePasswords": False,
                    "manage": True
                }],
            "type": 2,
            "accessAll": False,
            "externalId": "test.user02",
            "resetPasswordEnrolled": False,
            "permissions": None
        }
    ]
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api)

    members = offboard_handler.get_all_members()

    mock_logger.info.assert_called_once_with("Found 2 members in the organization")
    mock_api.get_users.assert_called_once()

    assert 'test.user01@example.com' in members
    assert 'test.user02@example.com' in members
    assert len(members) == 2


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_get_active_users(logger_mock: Mock):
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_api.get_active_user_report.return_value = ['test_user02@example.com']
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api)
    active_users = offboard_handler.get_active_users(90)

    mock_api.get_active_user_report.assert_called_once()

    assert len(active_users) == 1
    assert 'test_user02@example.com' in active_users
