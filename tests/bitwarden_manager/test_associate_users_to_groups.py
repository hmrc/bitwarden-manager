from unittest.mock import MagicMock

import pytest
import responses
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, UserType
from bitwarden_manager.associate_users_to_groups import AssociateUsersToGroups
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


MOCKED_LOGIN = responses.Response(
    method="POST",
    url="https://identity.bitwarden.com/connect/token",
    status=200,
    json={
        "access_token": "TEST_BEARER_TOKEN",
        "expires_in": 3600,
        "token_type": "Bearer",
    },
)

def test_associate_users_to_groups() -> None:
    event = {"event_name": "associate_users_to_groups",}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
            status=200,
            content_type="application/json",
        )

    AssociateUsersToGroups(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
    ).run(event)
    

    # rsps.assert_call_count("https://api.bitwarden.eu/public/members", 1) is True
    mock_client_bitwarden.associate_user_to_groups.called
    mock_client_bitwarden.list_existing_groups.called
    mock_client_bitwarden.list_existing_collections.called
    mock_client_bitwarden_vault.create_collections.called
    mock_client_bitwarden.collate_user_group_ids.called
    mock_client_bitwarden.get_groups.called


def test_associate_user_to_groups_rejects_bad_events() -> None:
    event = {"something?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        AssociateUsersToGroups(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
        ).run(event)

    assert not mock_client_bitwarden.associate_user_to_groups.called