from unittest.mock import MagicMock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, UserType
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


def test_onboard_user_invites_user_to_org() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        username="test.user", email="testemail@example.com", type=UserType.REGULAR_USER
    )


def test_onboard_non_admin_user_invites_user_to_org() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
        "team_admin": False,
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        username="test.user", email="testemail@example.com", type=UserType.REGULAR_USER
    )


def test_onboard_admin_user_invites_user_to_org() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
        "team_admin": True,
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        username="test.user", email="testemail@example.com", type=UserType.MANAGER
    )


def test_onboard_user_rejects_bad_events() -> None:
    event = {"something?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        OnboardUser(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
        ).run(event)

    assert not mock_client_bitwarden.invite_user.called


def test_onboard_user_rejects_bad_emails() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "not_an_email"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError):
        OnboardUser(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
        ).run(event)

    assert not mock_client_bitwarden.invite_user.called


def test_onboard_user_missing_collection_names() -> None:
    teams = ["Team Name One", "Team Name Two"]
    existing_collections = {"Team Name One": {"id": "ZZZZZZZZ", "externalID": ""}}
    expected = ["Team Name Two"]
    assert expected == OnboardUser._missing_collection_names(teams, existing_collections)
