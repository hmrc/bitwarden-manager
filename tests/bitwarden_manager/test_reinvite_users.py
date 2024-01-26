from unittest.mock import MagicMock, call

import pytest
from jsonschema.exceptions import ValidationError
from datetime import datetime

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.reinvite_users import ReinviteUsers


def test_reinvite_users() -> None:
    event = {"event_name": "reinvite_users"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    mock_client_bitwarden.get_pending_users = MagicMock(
        return_value=[
            {
                "object": "member",
                "id": "22222222",
                "userId": "",
                "name": "test user02",
                "email": "test.user02@example.com",
                "twoFactorEnabled": True,
                "status": 0,
                "collections": [],
                "type": 1,
                "accessAll": False,
                "externalId": "test.user02",
                "resetPasswordEnrolled": False,
            },
            {
                "object": "member",
                "id": "333333",
                "userId": "",
                "name": "test user03",
                "email": "test.user03@example.com",
                "twoFactorEnabled": True,
                "status": 0,
                "collections": [],
                "type": 1,
                "accessAll": False,
                "externalId": "test.user03",
                "resetPasswordEnrolled": False,
            },
        ]
    )

    mock_client_dynamodb.get_item_from_table = MagicMock(
        side_effect=[
            {"username": "test.user02", "invite_date": "2024-01-01"},
            {"username": "test.user03", "invite_date": datetime.today().strftime("%Y-%m-%d")},
        ]
    )

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called
    dynamodb_calls = [
        call(table_name="bitwarden", key={"username": "test.user02"}),
        call(table_name="bitwarden", key={"username": "test.user03"}),
    ]
    mock_client_dynamodb.get_item_from_table.assert_has_calls(dynamodb_calls)
    mock_client_bitwarden.reinvite_user.assert_called_with(id="22222222", username="test.user02")


def test_reinvite_users_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        ReinviteUsers(
            bitwarden_api=mock_client_bitwarden,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

        assert not mock_client_bitwarden.get_pending_users.assert_called
