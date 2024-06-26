from unittest.mock import MagicMock
from datetime import datetime

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.user import UmpUser


def test_onboard_user_invites_user_to_org() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        user=UmpUser(username="test.user", email="testemail@example.com", role="user")
    )


@pytest.mark.parametrize("role", [("user"), ("super_admin")])
def test_onboard_non_admin_user_invites_user_to_org(role: str) -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
        "role": role,
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        user=UmpUser(username="test.user", email="testemail@example.com", role=role)
    )


@pytest.mark.parametrize("role", [("team_admin"), ("all_team_admin")])
def test_onboard_team_admin_user_invites_user_to_org(role: str) -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
        "role": role,
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        user=UmpUser(username="test.user", email="testemail@example.com", role=role)
    )


def test_onboard_user_rejects_bad_events() -> None:
    event = {"something?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        OnboardUser(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

    assert not mock_client_bitwarden.invite_user.called


def test_onboard_user_rejects_bad_emails() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "not_an_email"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(ValidationError):
        OnboardUser(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

    assert not mock_client_bitwarden.invite_user.called


def test_onboard_user_writes_invite_date_to_db() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    date = datetime.today().strftime("%Y-%m-%d")
    mock_client_dynamodb.write_item_to_table.assert_called_with(
        table_name="bitwarden", item={"username": "test.user", "invite_date": date, "reinvites": 0}
    )
