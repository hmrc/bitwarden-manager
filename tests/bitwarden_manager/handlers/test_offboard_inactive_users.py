from unittest import mock
from unittest.mock import Mock, MagicMock

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.handlers.offboard_inactive_users import OffboardInactiveUsers


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test_offboard_users(logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_client = MagicMock(spec=BitwardenVaultClient)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client, dry_run=False)
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
    mock_client = MagicMock(spec=BitwardenVaultClient)
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client, dry_run=True)

    all_users = {"11111111": "user1@example.com", "22222222": "user2@example.com"}
    inactive_users = {"11111111", "22222222"}
    protected_users = {"22222222"}
    offboard_handler.offboard_users(inactive_users, all_users, protected_users)

    mock_logger.info.assert_any_call("DRY RUN: Would have offboarded 2 users")
    mock_logger.info.assert_any_call("Skipping offboarding Dry Run: user1@example.com")
    mock_logger.info.assert_any_call("Skipping offboarding of protected user user2@example.com")
    mock_api.remove_user_by_id.assert_not_called()


@mock.patch("bitwarden_manager.handlers.offboard_inactive_users.get_bitwarden_logger")
def test__get_protected_users(logger_mock: Mock) -> None:
    mock_logger = MagicMock()
    logger_mock.return_value = mock_logger

    mock_api = MagicMock(spec=BitwardenPublicApi)
    mock_api.get_users.return_value = [
        {"id": "1", "email": "user1@example.com", "collections": ["root-id"]},
        {"id": "2", "email": "user2@example.com", "collections": []},
    ]
    mock_api.get_users_by_group_name.return_value = ["3"]
    mock_client = MagicMock(spec=BitwardenVaultClient)
    mock_client.get_collection_id_by_name.return_value = "root-id"
    offboard_handler = OffboardInactiveUsers(bitwarden_api=mock_api, bitwarden_vault_client=mock_client, dry_run=True)
    protected_users = offboard_handler._get_protected_users()
    assert protected_users == {"1", "3"}
    mock_client.get_collection_id_by_name.assert_called_once_with("Root")
    mock_api.get_users.assert_called_once()
    mock_api.get_users_by_group_name.assert_called_once_with("MDTP Platform Owners")
