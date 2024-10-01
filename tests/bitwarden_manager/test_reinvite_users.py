from unittest.mock import MagicMock, Mock

import pytest
from jsonschema.exceptions import ValidationError
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.reinvite_users import MAX_INVITE_DURATION_IN_DAYS, MAX_REINVITES, ReinviteUsers


@freeze_time("2024-01-01")
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
            }
        ]
    )

    invite_date = datetime.today() - timedelta(days=MAX_INVITE_DURATION_IN_DAYS + 1)
    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={"username": "test.user02", "invite_date": invite_date.strftime("%Y-%m-%d"), "reinvites": 0}
    )

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called
    mock_client_dynamodb.get_item_from_table.assert_called_with(table_name="bitwarden", key={"username": "test.user02"})
    mock_client_bitwarden.reinvite_user.assert_called_with(id="22222222", username="test.user02")


def test_reinvite_pending_users_invite_not_expired_yet() -> None:
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
            }
        ]
    )

    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={"username": "test.user02", "invite_date": datetime.today().strftime("%Y-%m-%d"), "reinvites": 0}
    )

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called
    mock_client_dynamodb.get_item_from_table.assert_called_with(table_name="bitwarden", key={"username": "test.user02"})
    assert not mock_client_bitwarden.reinvite_user.called


def test_reinvite_pending_users_already_reinvited_max_reinvite_times() -> None:
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
            }
        ]
    )

    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={"username": "test.user02", "invite_date": "2024-01-01", "reinvites": MAX_REINVITES}
    )

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called
    mock_client_dynamodb.get_item_from_table.assert_called_with(table_name="bitwarden", key={"username": "test.user02"})
    assert not mock_client_bitwarden.reinvite_user.called
    mock_client_bitwarden.remove_user.assert_called_with(username="test.user02")


def test_reinvite_pending_users_already_reinvited_max_reinvite_times_but_not_yet_expired() -> None:
    event = {"event_name": "reinvite_users"}
    mock_client_bitwarden = MagicMock(spec=BitwardenPublicApi)
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)
    # 14 = Original 5 days, plus 5 after first invite, plus 5 after second reinvite (max 2)
    date = datetime.today() - timedelta(days=14)
    date_str = date.strftime("%Y-%m-%d")

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
            }
        ]
    )

    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={
            "username": "test.user02",
            "invite_date": date_str,
            "reinvites": MAX_REINVITES,
            "total_invites": 1,
        }
    )

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_bitwarden.get_pending_users.assert_called
    mock_client_dynamodb.get_item_from_table.assert_called_with(table_name="bitwarden", key={"username": "test.user02"})
    assert not mock_client_bitwarden.reinvite_user.called
    assert not mock_client_bitwarden.remove_user.called


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


def test_reinvite_pending_users_not_in_dynamodb() -> None:
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
            }
        ]
    )

    mock_client_dynamodb.get_item_from_table = MagicMock(return_value={})

    ReinviteUsers(
        bitwarden_api=mock_client_bitwarden,
        dynamodb_client=mock_client_dynamodb,
    ).run(event)

    mock_client_dynamodb.get_item_from_table.assert_called_with(table_name="bitwarden", key={"username": "test.user02"})
    assert not mock_client_bitwarden.reinvite_user.called



@pytest.mark.parametrize(
    "invite_date,today,reinvites,expected", 
    [
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 10, tzinfo=timezone.utc), 0, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 11, tzinfo=timezone.utc), 0, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 12, tzinfo=timezone.utc), 0, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 15, tzinfo=timezone.utc), 0, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 0, True), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 20, tzinfo=timezone.utc), 0, True),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 10, tzinfo=timezone.utc), 1, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 11, tzinfo=timezone.utc), 1, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 12, tzinfo=timezone.utc), 1, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 15, tzinfo=timezone.utc), 1, False),
        
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 1, True), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 20, tzinfo=timezone.utc), 1, True),  
    ]  
)
def test_has_invite_expired(invite_date: datetime, today: datetime,reinvites: int, expected: bool) -> None:
     assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=Mock(),
    ).has_invite_expired(invite_date=invite_date, today=today, reinvites=reinvites)

# if invite_date < date and reinvites < MAX_REINVITES:
@pytest.mark.parametrize(
    "invite_date,today,reinvites,expected", 
    [
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 10, tzinfo=timezone.utc), 0, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 11, tzinfo=timezone.utc), 0, False), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 12, tzinfo=timezone.utc), 0, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 15, tzinfo=timezone.utc), 0, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 0, True), 
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 1, True),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 2, False),
        (datetime(2024, 4, 10, tzinfo=timezone.utc), datetime(2024, 4, 16, tzinfo=timezone.utc), 3, False),
    ]  
)
def test_can_reinvite_user(invite_date: datetime,today: datetime,reinvites: int,expected: bool) -> None:
    mock_client_dynamodb = MagicMock(spec=DynamodbClient)
    mock_client_dynamodb.get_item_from_table = MagicMock(
        return_value={"username": "test.user", "invite_date": "2024-04-10", "reinvites": 0, "total_invites": 0}
    )
    assert expected == ReinviteUsers(
        bitwarden_api=Mock(),
        dynamodb_client=mock_client_dynamodb,
    ).can_reinvite_user(invite_date,today,reinvites)



    # invite_date | date  | reinvite | max_reinvites | expected_outcome 
    # t           | t - 5 | 0        | 5             | false
    # t           | t - 2 | 0        | 5             | false
    # t           | t - 1 | 0        | 5             | false
    # t           | t     | 0        | 5             | false
    # t           | t + 1 | 0        | 5             | true
    # t           | t + 2 | 0        | 5             | true
    # t           | t + 1 | 5        | 5             | false
    # t           | t + 2 | 6        | 5             | false


 


