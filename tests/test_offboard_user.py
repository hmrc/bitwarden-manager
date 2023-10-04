from unittest.mock import MagicMock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.offboard_user import OffboardUser


def test_offboard_user_removes_user_from_org() -> None:
    event = {
        "event_name": "remove_user",
        "username": "test.user",
        "email": "testemail@example.com",
    }
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)

    OffboardUser(
        bitwarden_api=mock_client_bitwarden,
    ).run(event)

    mock_client_bitwarden.remove_user.assert_called_with(username="test.user", email="testemail@example.com")


def test_onboard_user_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        OffboardUser(
            bitwarden_api=mock_client_bitwarden,
        ).run(event)

    assert not mock_client_bitwarden.remove_user.called


def test_onboard_user_rejects_bad_emails() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "not_an_email"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)

    with pytest.raises(ValidationError):
        OffboardUser(
            bitwarden_api=mock_client_bitwarden,
        ).run(event)

    assert not mock_client_bitwarden.remove_user.called