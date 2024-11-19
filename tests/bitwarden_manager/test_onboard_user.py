from unittest.mock import MagicMock, Mock
from datetime import datetime
from freezegun import freeze_time
import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import (
    BitwardenPublicApi,
    BitwardenUserAlreadyExistsException,
    BitwardenUserNotFoundException,
)
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

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(side_effect=BitwardenUserNotFoundException("No user with externalId test.user found")),
    )
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)
    mock_client_user_management = MagicMock(
        spec=UserManagementApi,
        get_user_teams=Mock(return_value=["team-one"]),
        get_user_role_by_team=Mock(return_value="user"),
    )

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.invite_user.assert_called_with(
        user=UmpUser(username="test.user", email="testemail@example.com", roles_by_team={"team-one": "user"})
    )


def test_onboard_user_rejects_bad_events() -> None:
    event = {"something?": 1}

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(side_effect=BitwardenUserNotFoundException("No user with externalId test.user found")),
    )
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

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(side_effect=BitwardenUserNotFoundException("No user with externalId test.user found")),
    )
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


@freeze_time("2024-03-11")
def test_onboard_user_writes_invite_date_to_db_for_previously_invited_user() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(side_effect=BitwardenUserNotFoundException("No user with externalId test.user found")),
    )
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(
        spec=DynamodbClient,
        get_item_from_table=Mock(
            return_value={
                "username": event.get("username"),
                "invite_date": datetime.today().strftime("%Y-%m-%d"),
                "reinvites": 2,
                "total_invites": 3,
            }
        ),
    )

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_dynamodb.add_item_to_table.assert_called_with(
        item={
            "username": "test.user",
            "invite_date": datetime.today().strftime("%Y-%m-%d"),
            "reinvites": 0,
            "total_invites": 4,
        }
    )


def test_onboard_user_writes_invite_date_to_db_for_first_time_user_invite() -> None:
    event = {
        "event_name": "new_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(side_effect=BitwardenUserNotFoundException("No user with externalId test.user found")),
    )
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)
    mock_client_dynamodb.get_item_from_table = MagicMock(return_value={})

    OnboardUser(
        bitwarden_api=mock_client_bitwarden,
        user_management_api=mock_client_user_management,
        bitwarden_vault_client=mock_client_bitwarden_vault,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_dynamodb.add_item_to_table.assert_called_with(
        item={
            "username": "test.user",
            "invite_date": datetime.today().strftime("%Y-%m-%d"),
            "reinvites": 0,
            "total_invites": 1,
        },
    )


def test_onboard_user_exits_if_user_exists_in_bitwarden() -> None:
    event = {
        "event_name": "new_user",
        "username": "existing.user",
        "email": "existing.user@example.com",
    }

    mock_client_bitwarden = MagicMock(
        spec=BitwardenPublicApi,
        get_user_by=Mock(
            return_value={
                "email": "existing.user@example.com",
                "externalId": "existing.user",
            }
        ),
    )
    mock_client_user_management = MagicMock(spec=UserManagementApi)
    mock_client_bitwarden_vault = MagicMock(spec=BitwardenVaultClient)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(BitwardenUserAlreadyExistsException, match="User existing.user already exists."):
        OnboardUser(
            bitwarden_api=mock_client_bitwarden,
            user_management_api=mock_client_user_management,
            bitwarden_vault_client=mock_client_bitwarden_vault,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

    assert not mock_client_bitwarden.invite_user.called
