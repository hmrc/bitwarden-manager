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
    offboard_handler.offboard_users(inactive_users, all_users, set())

    mock_logger.info.assert_any_call("Removing user user1@example.com from bitwarden")
    mock_logger.info.assert_any_call("Removing user user2@example.com from bitwarden")


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_offboard_users_dry_run(logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, dry_run=True)

    all_users = {"11111111": "user1@example.com", "22222222": "user2@example.com"}
    inactive_users = {"11111111", "22222222"}
    protected_users = {"22222222"}
    offboard_handler.offboard_users(inactive_users, all_users, protected_users)

    mock_logger.info.assert_any_call("DRY RUN: Would have offboarded 2 users")
    mock_logger.info.assert_any_call("Skipping offboarding Dry Run: user1@example.com")
    mock_logger.info.assert_any_call("Skipping offboarding of protected user user2@example.com")
    mock_api.remove_user_by_id.assert_not_called()
