from unittest.mock import Mock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.onboard_user import OnboardUser


def test_onboard_user_invites_user_to_org() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "testemail@example.com"}
    mock_client = Mock(spec=BitwardenPublicApi)

    OnboardUser(bitwarden_api=mock_client).run(event)

    mock_client.invite_user.assert_called_with(username="test.user", email="testemail@example.com")


def test_onboard_user_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client = Mock(spec=BitwardenPublicApi)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        OnboardUser(bitwarden_api=mock_client).run(event)

    assert not mock_client.invite_user.called


def test_onboard_user_rejects_bad_emails() -> None:
    event = {"event_name": "new_user", "username": "test.user", "email": "not_an_email"}
    mock_client = Mock(spec=BitwardenPublicApi)

    with pytest.raises(ValidationError):
        OnboardUser(bitwarden_api=mock_client).run(event)

    assert not mock_client.invite_user.called