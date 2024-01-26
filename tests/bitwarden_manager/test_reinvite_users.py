from unittest.mock import MagicMock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.reinvite_users import ReinviteUsers


def test_reinvite_users() -> None:
    event = {"event_name": "reinvite_users"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called


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
