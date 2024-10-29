from trace import Trace
from typing import Dict
from unittest.mock import MagicMock, Mock

import pytest
from jsonschema.exceptions import ValidationError
from datetime import datetime
from freezegun import freeze_time
from moto.appmesh.dataclasses.virtual_node import Trust

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.reinvite_users import (
    INVITE_VALID_DURATION_IN_DAYS,
    MAX_INVITES_PER_RUN,
    MAX_INVITES_TOTAL,
    ReinviteUsers,
)


def get_event() -> Dict[str, str]:
    return {"event_name": "reinvite_users"}


def test_rejects_bad_events() -> None:
    event = {"something?": 1}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    with pytest.raises(ValidationError, match="'event_name' is a required property"):
        ReinviteUsers(
            bitwarden_api=mock_client_bitwarden,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

        assert not mock_client_bitwarden.get_pending_users.assert_called


def test_pending_user_not_in_dynamodb_gets_removed() -> None:
    event = get_event()
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    bitwarden_user = {
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
    }

    mock_client_dynamodb.get_item_from_table = MagicMock(return_value={})
    mock_client_bitwarden.get_pending_users = MagicMock(return_value=[bitwarden_user])
    mock_client_bitwarden.remove_user = MagicMock()

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_dynamodb.get_item_from_table.assert_called_with(
        username=bitwarden_user.get("externalId"),
    )

    mock_client_bitwarden.remove_user.assert_called_with(username=bitwarden_user.get("externalId"))

    assert not mock_client_bitwarden.reinvite_user.called


@pytest.mark.parametrize(
    "invite_date,today,invites,total_invites,expected,user_removed",
    [
        # test date
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS - 1)),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            False,
            False,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + INVITE_VALID_DURATION_IN_DAYS),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            False,
            False,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            True,
            False,
        ),
        # test max per run
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            True,
            False,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            MAX_INVITES_PER_RUN,
            (MAX_INVITES_TOTAL - 1),
            False,
            True,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN + 1),
            (MAX_INVITES_TOTAL - 1),
            False,
            True,
        ),
        # test max total
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            True,
            False,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN - 1),
            MAX_INVITES_TOTAL,
            False,
            True,
        ),
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL + 1),
            False,
            True,
        ),
        # test all max or expired
        (
            datetime(2024, 4, 10),
            datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)),
            MAX_INVITES_PER_RUN,
            MAX_INVITES_TOTAL,
            False,
            True,
        ),
    ],
)
def test_invite_user(
    invite_date: datetime, today: datetime, invites: int, total_invites: int, expected: bool, user_removed: bool
) -> None:
    event = get_event()
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)

    bitwarden_user = {
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
    }

    mock_client_bitwarden.get_pending_users = MagicMock(return_value=[bitwarden_user])

    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={
            "username": bitwarden_user.get("name"),
            "invite_date": invite_date.strftime("%Y-%m-%d"),
            "reinvites": invites,
            "total_invites": total_invites,
        }
    )

    with freeze_time(today):
        ReinviteUsers(
            bitwarden_api=mock_client_bitwarden,
            dynamodb_client=mock_client_dynamodb,
        ).run(event)

        mock_client_bitwarden.get_pending_users.assert_called()
        mock_client_dynamodb.get_item_from_table.assert_called_with(username=bitwarden_user.get("externalId"))

        if expected is True:
            mock_client_bitwarden.reinvite_user.assert_called_with(
                id=bitwarden_user.get("id"), username=bitwarden_user.get("externalId")
            )
        else:
            mock_client_bitwarden.reinvite_user.assert_not_called()

        if user_removed is True:
            mock_client_bitwarden.remove_user.assert_called_with(username=bitwarden_user.get("externalId"))
        else:
            mock_client_bitwarden.remove_user.assert_not_called()


@pytest.mark.parametrize(
    "invite_date,today,expected",
    [
        (datetime(2024, 4, 10), datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS - 1)), False),
        (datetime(2024, 4, 10), datetime(2024, 4, 10 + INVITE_VALID_DURATION_IN_DAYS), False),
        (datetime(2024, 4, 10), datetime(2024, 4, 10 + (INVITE_VALID_DURATION_IN_DAYS + 1)), True),
    ],
)
def test_has_invite_expired(invite_date: datetime, today: datetime, expected: bool) -> None:
    with freeze_time(today.strftime("%Y-%m-%d")):
        assert expected == ReinviteUsers(
            bitwarden_api=Mock(),
            dynamodb_client=Mock(),
        ).has_invite_expired(invite_date=invite_date)


@pytest.mark.parametrize(
    "invites,expected",
    [
        (MAX_INVITES_PER_RUN - 1, False),
        (MAX_INVITES_PER_RUN, True),
        (MAX_INVITES_PER_RUN + 1, True),
    ],
)
def test_has_reached_max_invites_per_run(invites: int, expected: bool) -> None:
    assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=Mock(),
    ).has_reached_max_invites_per_run(invites=invites)


@pytest.mark.parametrize(
    "invites,expected",
    [
        (MAX_INVITES_TOTAL - 1, False),
        (MAX_INVITES_TOTAL, True),
        (MAX_INVITES_TOTAL + 1, True),
    ],
)
def test_has_reached_max_total_invites(invites: int, expected: bool) -> None:
    assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=Mock(),
    ).has_reached_max_total_invites(invites=invites)


@pytest.mark.parametrize(
    "invites,total_invites,expected",
    [
        # test max per run
        (
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            True,
        ),
        (
            MAX_INVITES_PER_RUN,
            (MAX_INVITES_TOTAL - 1),
            False,
        ),
        (
            (MAX_INVITES_PER_RUN + 1),
            (MAX_INVITES_TOTAL - 1),
            False,
        ),
        # test max total
        (
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL - 1),
            True,
        ),
        (
            (MAX_INVITES_PER_RUN - 1),
            MAX_INVITES_TOTAL,
            False,
        ),
        (
            (MAX_INVITES_PER_RUN - 1),
            (MAX_INVITES_TOTAL + 1),
            False,
        ),
        # test min and max
        (
            0,
            0,
            True,
        ),
        (
            MAX_INVITES_PER_RUN,
            MAX_INVITES_TOTAL,
            False,
        ),
    ],
)
def test_is_eligible(invites: int, total_invites: int, expected: bool) -> None:
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)
    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={
            "username": "test.user",
            "invite_date": "2024-04-10",
            "reinvites": invites,
            "total_invites": total_invites,
        }
    )

    assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=mock_client_dynamodb,
    ).is_eligible(invites_this_run=invites, total_invites=total_invites)


@pytest.mark.parametrize(
    "date, expected_year, expected_month, expected_day",
    [
        ("2024-04-10", 2024, 4, 10),
        ("1970-01-01", 1970, 1, 1),
    ],
)
def test_str_to_datetime(date: str, expected_year: int, expected_month: int, expected_day: int) -> None:
    assert datetime(expected_year, expected_month, expected_day) == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=Mock(),
    ).str_to_datetime(date=date)


@pytest.mark.parametrize(
    "date, expected",
    [
        (datetime(2024, 4, 10), "2024-04-10"),
        (datetime(1970, 1, 1), "1970-01-01"),
    ],
)
def test_datetime_to_str(date: datetime, expected: str) -> None:
    assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=Mock(),
    ).datetime_to_str(date=date)
