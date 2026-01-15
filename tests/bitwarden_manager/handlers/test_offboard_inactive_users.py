from unittest import mock
from unittest.mock import Mock, MagicMock

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.handlers.offboard_inactive_users import OffboardInactiveUsers


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_offboard_users(logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, dry_run=False)
    all_users = {"11111111": "user1@example.com", "22222222": "user2@example.com"}
    inactive_users = {"11111111", "22222222"}
    offboard_handler.offboard_users(inactive_users, all_users)

    mock_logger.info.assert_any_call("Removing user user1@example.com from bitwarden")
    mock_logger.info.assert_any_call("Removing user user2@example.com from bitwarden")
