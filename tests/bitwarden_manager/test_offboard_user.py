from unittest.mock import MagicMock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.offboard_user import OffboardUser


def test_offboard_user_removes_user_from_org() -> None:
    event = {
        "event_name": "remove_user",
        "username": "test.user",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OffboardUser(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.remove_user.assert_called_with(username="test.user")


def test_offboard_user_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        OffboardUser(
            bitwarden_api=mock_client_bitwarden,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

    assert not mock_client_bitwarden.remove_user.called


def test_offboard_user_removes_item_from_dynamodb() -> None:
    event = {
        "event_name": "remove_user",
        "username": "test.user",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    OffboardUser(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_dynamodb.delete_item_from_table.assert_called_with(
        table_name="bitwarden", key={"username": "test.user"}
    )
