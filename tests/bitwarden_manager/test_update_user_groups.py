from unittest.mock import MagicMock
from typing import List

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.update_user_groups import UpdateUserGroups
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


def test_update_user_groups() -> None:
    event = {
        "event_name": "update_user_groups",
        "username": "test.user",
        "email": "testemail@example.com",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    UpdateUserGroups(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
    ).run(event)

    user_id = mock_client_bitwarden.fetch_user_id_by_email()
    managed_group_ids = mock_client_bitwarden.collate_user_group_ids()
    custom_group_ids: List[str] = []

    mock_client_bitwarden.associate_user_to_groups.assert_called_with(
        user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
    )


def test_update_user_groups_rejects_bad_events() -> None:
    event = {"something?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        UpdateUserGroups(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
        ).run(event)

    assert not mock_client_bitwarden.associate_user_to_groups.called


def test_update_user_groups_rejects_bad_emails() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "not_an_email"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError):
        UpdateUserGroups(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
        ).run(event)

    assert not mock_client_bitwarden.associate_user_to_groups.called
