import pytest
from _pytest.logging import LogCaptureFixture

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from bitwarden_manager.confirm_user import ConfirmUser, BitwardenConfirmUserInvalidDomain
from unittest.mock import Mock, MagicMock
from jsonschema.exceptions import ValidationError


def test_list_users() -> None:
    event = {"event_name": "confirm_user"}
    mock_client = MagicMock(spec=BitwardenVaultClient)
    ConfirmUser(bitwarden_vault_client=mock_client, allowed_domains=["example.co.uk"]).run(event)

    assert mock_client.list_unconfirmed_users.called


def test_confirm_user() -> None:
    event = {"event_name": "confirm_user"}
    mock_client = MagicMock(spec=BitwardenVaultClient)

    mock_client.list_unconfirmed_users = MagicMock(return_value=[{"email": "test@example.co.uk", "id": "example_id"}])
    ConfirmUser(bitwarden_vault_client=mock_client, allowed_domains=["example.co.uk"]).run(event)

    mock_client.confirm_user.assert_called_with(user_id="example_id")


def test_confirm_user_invalid_domain() -> None:
    event = {"event_name": "confirm_user"}
    mock_client = MagicMock(spec=BitwardenVaultClient)

    mock_client.list_unconfirmed_users = MagicMock(
        return_value=[
            {"email": "test@invaliddomain.co.uk", "id": "example_id"},
            {"email": "test@example.co.uk@invaliddomain.co.uk", "id": "example_id"},
        ]
    )
    with pytest.raises(ExceptionGroup, match="User Confirmation Errors: ") as exception_group:
        ConfirmUser(bitwarden_vault_client=mock_client, allowed_domains=["example.co.uk"]).run(event)
        assert exception_group.exception[0] is BitwardenConfirmUserInvalidDomain

    assert mock_client.confirm_user.call_count == 0


def test_confirm_user_handles_errors(caplog: LogCaptureFixture) -> None:
    event = {"event_name": "confirm_user"}
    mock_client = MagicMock(spec=BitwardenVaultClient)

    mock_client.list_unconfirmed_users = MagicMock(
        return_value=[
            {"email": "test@example.co.uk", "id": "example_id"},
            {"email": "test2@example.co.uk", "id": "example_id2"},
            {"email": "test3@invalidexample.co.uk", "id": "example_id2"},
        ]
    )

    mock_client.confirm_user = MagicMock(side_effect=BitwardenVaultClientError())

    with pytest.raises(ExceptionGroup, match="User Confirmation Errors: ") as exception_group:
        ConfirmUser(bitwarden_vault_client=mock_client, allowed_domains=["example.co.uk"]).run(event)
        assert exception_group.exception[0] is BitwardenVaultClientError
        assert exception_group.exception[1] is BitwardenVaultClientError
        assert exception_group.exception[2] is BitwardenConfirmUserInvalidDomain

    assert mock_client.confirm_user.call_count == 2


def test_confirm_user_validates_events() -> None:
    event = {"event_name": "not the right event"}
    mock_client = Mock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'not the right event' does not match 'confirm_user'"):
        ConfirmUser(bitwarden_vault_client=mock_client, allowed_domains=["example.com"]).run(event)

    assert not mock_client.confirm_user.called
