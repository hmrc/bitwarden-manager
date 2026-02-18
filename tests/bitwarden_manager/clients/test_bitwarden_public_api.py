import base64
import logging
from typing import Any, Dict, List

import os
from unittest.mock import patch, Mock

import pytest
import responses
from _pytest.logging import LogCaptureFixture
from freezegun import freeze_time
from mock import MagicMock
from requests import HTTPError
from responses import matchers

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, BitwardenUserNotFoundException
from bitwarden_manager.user import UmpUser


MOCKED_LOGIN = responses.Response(
    method="POST",
    url="https://identity.bitwarden.eu/connect/token",
    status=200,
    json={
        "access_token": "TEST_BEARER_TOKEN",
        "expires_in": 3600,
        "token_type": "Bearer",
    },
)

MOCKED_GET_MEMBERS = responses.Response(
    status=200,
    content_type="application/json",
    method=responses.GET,
    url="https://api.bitwarden.eu/public/members",
    body=open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")).read(),
)

MOCKED_EVENTS = responses.Response(
    status=200,
    content_type="application/json",
    method=responses.GET,
    url="https://api.bitwarden.eu/public/events",
    json={
        "object": "list",
        "data": [
            {
                "object": "event",
                "type": 1000,
                "itemId": "3767a302-8208-4dc6-b842-030428a1cfad",
                "memberId": None,
                "actingUserId": "11111111",
            }
        ],
    },
)


def test_get_user_by_email() -> None:
    email = "test.user01@example.com"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user = client.get_user_by_email(email=email)

        assert email == user["email"]
        assert "11111111" == user["id"]

        with pytest.raises(Exception, match=r"No user with email .* found"):
            client.get_user_by_email(email="does.not.exist@example.com")


def test_get_user_collections_returns_empty_list_when_collections_are_none() -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    result = client._BitwardenPublicApi__get_user_collections(None)  # type: ignore
    assert result == []


def test_get_user_collections_returns_collections_where_collections_exist() -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    user_colletions = [_user_collection("manually-created"), _user_collection("manager-created")]

    collections = [
        _collection_object_with_empty_external_id("manually-created"),
        _collection_object_with_base64_encoded_external_id("manager-created"),
    ]

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        for collection in collections:
            rsps.add(
                status=200,
                content_type="application/json",
                method=rsps.GET,
                url=f"https://api.bitwarden.eu/public/collections/{collection["id"]}",
                json=collection,
            )

        result = client._BitwardenPublicApi__get_user_collections(user_colletions)  # type: ignore
        assert result == collections


def test_get_user_collections_throws_exception_when_collections_dont_exist() -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    user_collections = [_user_collection("non-existent")]

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            rsps.GET,
            f"https://api.bitwarden.eu/public/collections/{user_collections[0]["id"]}",
            status=404,
        )

        client._BitwardenPublicApi__get_user_collections(None)  # type: ignore
        with pytest.raises(Exception, match=r"Failed to get collection"):
            client._BitwardenPublicApi__get_user_collections(user_collections)  # type: ignore


def test_fetch_user_id_by_email() -> None:
    email = "test.user01@example.com"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user_id = client.fetch_user_id_by_email(email=email)

        assert user_id == "11111111"


def test_get_user_by_external_id() -> None:
    external_id = "test.user01"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user = client.get_user_by_external_id(external_id=external_id)

        assert external_id == user["externalId"]
        assert "11111111" == user["id"]

        with pytest.raises(Exception, match=r"No user with external_id .* found"):
            client.get_user_by_external_id(external_id="")


def test__get_events() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_EVENTS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        events = client._get_events("2026-01-01", 10)

        assert len(events) == 1
        assert events[0]["actingUserId"] == "11111111"


def test__get_event_end_date() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_EVENTS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        events = client._get_events("2026-01-01", 10, "2026-01-02")
        assert len(events) == 1
        assert events[0]["actingUserId"] == "11111111"


@patch("bitwarden_manager.clients.bitwarden_public_api.session.get")
def test_get_events_pagination(mock_get: Mock) -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    # First call returns a continuation token
    response_1 = MagicMock()
    response_1.status_code = 200
    response_1.json.return_value = {"data": [{"id": "event_page_1"}], "continuationToken": "token_for_page_2"}

    # Second call returns no continuation token
    response_2 = MagicMock()
    response_2.status_code = 200
    response_2.json.return_value = {"data": [{"id": "event_page_2"}], "continuationToken": None}

    mock_get.side_effect = [response_1, response_2]

    events = client._get_events(start_date="2026-01-01")

    assert len(events) == 2
    assert events[0]["id"] == "event_page_1"
    assert events[1]["id"] == "event_page_2"

    # Verify calls
    assert mock_get.call_count == 2

    # Check that the second call used the continuationToken
    args, kwargs = mock_get.call_args_list[1]
    assert kwargs["params"]["continuationToken"] == "token_for_page_2"


@patch("bitwarden_manager.clients.bitwarden_public_api.session.get")
def test_get_events_success(mock_get: Mock) -> None:
    mock_logger = MagicMock()
    bitwarden_api = BitwardenPublicApi(
        logger=mock_logger,
        client_id="foo",
        client_secret="bar",
    )
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "event1", "actingUserId": "user1"},
            {"id": "event2", "actingUserId": "user2"},
        ],
        "continuationToken": None,
    }
    mock_get.return_value = mock_response

    start_date = "2023-01-01"
    events = bitwarden_api._get_events(start_date=start_date)

    # Assertions
    assert len(events) == 2
    assert events[0]["id"] == "event1"
    assert events[1]["id"] == "event2"
    mock_logger.info.assert_called_with("Successfully fetched 2 events for time range: 2023-01-01 to now")


@patch("bitwarden_manager.clients.bitwarden_public_api.session.get")
def test_get_events_rate_limit(mock_get: Mock) -> None:
    mock_logger = MagicMock()
    bitwarden_api = BitwardenPublicApi(
        logger=mock_logger,
        client_id="foo",
        client_secret="bar",
    )
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "1"}
    mock_get.side_effect = [
        mock_response,
        MagicMock(status_code=200, json=lambda: {"data": [], "continuationToken": None}),
    ]

    start_date = "2023-01-01"
    events = bitwarden_api._get_events(start_date=start_date)

    # Assertions
    assert len(events) == 0
    mock_logger.warning.assert_called_with("Rate limit hit. Waiting 1 seconds before retrying...")


@patch("bitwarden_manager.clients.bitwarden_public_api.session.get")
def test_get_events_http_error(mock_get: Mock) -> None:
    bitwarden_api = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = HTTPError("Internal Server Error")
    mock_get.return_value = mock_response

    start_date = "2023-01-01"
    with pytest.raises(Exception, match="Failed to retrieve events report"):
        bitwarden_api._get_events(start_date=start_date)


@freeze_time("2026-01-14")
def test_get_active_user_report() -> None:
    mock_logger = MagicMock()

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_EVENTS)

        client = BitwardenPublicApi(
            logger=mock_logger,
            client_id="foo",
            client_secret="bar",
        )
        active_users = client.get_active_user_report(30)

        mock_logger.info.assert_any_call("Fetching events for time range: 2025-12-15 to now")
        mock_logger.info.assert_any_call("Retrieved 1 events from page 1")
        mock_logger.info.assert_any_call("Successfully fetched 1 events for time range: 2025-12-15 to now")
        assert mock_logger.info.call_count == 3

        assert len(active_users) == 1
        assert "11111111" in active_users


def test_grant_can_manage_permission_to_team_collections_to_team_admin() -> None:
    member_id = "22222222"
    teams = ["team-one", "team-two"]
    user = UmpUser(
        username="test.user02",
        email="test.user02@example.com",
        roles_by_team={"team-one": "team_admin", "team-two": "all_team_admin"},
    )
    user_collections = [
        _collection_object_with_empty_external_id("manually-created", groups=[]),
        _collection_object_with_base64_encoded_external_id("manager-created", groups=[]),
    ]

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        rsps.add(
            status=200,
            content_type="application/json",
            method=rsps.GET,
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id("team-one", groups=[]),
                    _collection_object_with_base64_encoded_external_id("team-two", groups=[]),
                    _collection_object_with_base64_encoded_external_id("manager-created", groups=[]),
                    _collection_object_with_empty_external_id("manually-created", groups=[]),
                ]
            },
        )

        for collection in user_collections:
            rsps.add(
                status=200,
                content_type="application/json",
                method=rsps.GET,
                url=f"https://api.bitwarden.eu/public/collections/{collection["id"]}",
                json=collection,
            )

        rsps.add(
            status=200,
            content_type="application/json",
            method=rsps.PUT,
            url=f"https://api.bitwarden.eu/public/members/{member_id}",
            match=[
                matchers.json_params_matcher(
                    {
                        "type": 2,
                        "externalId": user.username,
                        "resetPasswordEnrolled": False,
                        "permissions": None,
                        "collections": [
                            _user_collection(name="team-one", readOnly=False, manage=True),
                            _user_collection(name="team-two", readOnly=False, manage=True),
                            _user_collection(name="manually-created", readOnly=False, manage=True),
                        ],
                        # "groups": [],
                    }
                )
            ],
            json={
                "type": 2,
                "externalId": user.username,
                "resetPasswordEnrolled": True,
                "permissions": None,
                "object": "member",
                "id": member_id,
                "userId": "user-id",
                "name": "Test User",
                "email": user.email,
                "twoFactorEnabled": True,
                "status": 0,
                "collections": [
                    _user_collection(name="team-one", readOnly=False, manage=True),
                    _user_collection(name="team-two", readOnly=False, manage=True),
                    _user_collection(name="manually-created", readOnly=False, manage=True),
                ],
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.grant_can_manage_permission_to_team_collections(
            user=user,
            teams=teams,
        )

        assert rsps.calls[-1].request.method == "PUT"
        assert rsps.calls[-1].request.url == f"https://api.bitwarden.eu/public/members/{member_id}"

        rsps.add(
            status=400,
            content_type="application/json",
            method=rsps.PUT,
            url=f"https://api.bitwarden.eu/public/members/{member_id}",
            json={"error": "error"},
        )

        with pytest.raises(Exception, match='Failed to grant "can manage" permission to user'):
            client.grant_can_manage_permission_to_team_collections(
                user=user,
                teams=teams,
            )

        rsps.add(
            status=200,
            content_type="application/json",
            method=rsps.GET,
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id("team-one", groups=[]),
                    _collection_object_with_base64_encoded_external_id("team-one", groups=[]),
                ]
            },
        )

        with pytest.raises(Exception, match="Duplicate collection found"):
            client.grant_can_manage_permission_to_team_collections(
                user=user,
                teams=teams,
            )


def test_grant_can_manage_permission_to_team_collections_to_regular_user() -> None:
    teams = ["team-one", "team-two"]
    user = UmpUser(
        username="test.user02",
        email="test.user02@example.com",
        roles_by_team={"team-one": "user", "team-two": "super_admin"},
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id("team-one", groups=[]),
                    _collection_object_with_base64_encoded_external_id("team-two", groups=[]),
                ]
            },
        )
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.grant_can_manage_permission_to_team_collections(
            user=user,
            teams=teams,
        )

        assert len(rsps.calls) == 1
        assert rsps.calls[0].request.method != "PUT"


def test_assign_custom_permissions_to_platsec_user() -> None:
    member_id = "22222222"
    teams = ["Platform Security", "team-two"]
    user = UmpUser(
        username="test.user02",
        email="test.user02@example.com",
        roles_by_team={"Platform Security": "user", "team-two": "super_admin"},
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        rsps.add(
            status=200,
            content_type="application/json",
            method=rsps.PUT,
            url=f"https://api.bitwarden.eu/public/members/{member_id}",
            match=[
                matchers.json_params_matcher(
                    {
                        "type": 4,
                        "permissions": {
                            "accessEventLogs": True,
                            "accessImportExport": False,
                            "accessReports": True,
                            "createNewCollections": False,
                            "editAnyCollection": False,
                            "deleteAnyCollection": False,
                            "manageGroups": False,
                            "managePolicies": False,
                            "manageSso": False,
                            "manageUsers": True,
                            "manageResetPassword": True,
                            "manageScim": False,
                        },
                    }
                )
            ],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.assign_custom_permissions_to_platsec_user(
            user=user,
            teams=teams,
        )

        assert len(rsps.calls) == 3
        assert rsps.calls[-1].request.method == "PUT"
        assert rsps.calls[-1].request.url == f"https://api.bitwarden.eu/public/members/{member_id}"

        rsps.add(
            status=400,
            content_type="application/json",
            method=rsps.PUT,
            url=f"https://api.bitwarden.eu/public/members/{member_id}",
            json={"error": "error"},
        )

        with pytest.raises(Exception, match="Failed to grant custom permissions to PlatSec user"):
            client.assign_custom_permissions_to_platsec_user(
                user=user,
                teams=teams,
            )


def test_assign_custom_permissions_to_platsec_admin() -> None:
    teams = ["Platform Security", "team-two"]
    user = UmpUser(
        username="test.user01",
        email="test.user01@example.com",
        roles_by_team={"Platform Security": "team_admin", "team-two": "super_admin"},
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.assign_custom_permissions_to_platsec_user(
            user=user,
            teams=teams,
        )

        assert len(rsps.calls) == 2
        assert rsps.calls[-1].request.method != "PUT"


def test_assign_custom_permissions_to_non_platsec_user() -> None:
    teams = ["team-one", "team-two"]
    user = UmpUser(
        username="test.user02",
        email="test.user02@example.com",
        roles_by_team={"team-one": "user", "team-two": "super_admin"},
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.assign_custom_permissions_to_platsec_user(
            user=user,
            teams=teams,
        )

        assert len(rsps.calls) == 2
        assert rsps.calls[-1].request.method != "PUT"


def test_invite_user() -> None:
    test_user = "test.user"
    test_email = "test@example.com"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            match=[
                matchers.json_params_matcher(
                    {
                        "type": 2,
                        "resetPasswordEnrolled": True,
                        "externalId": test_user,
                        "email": test_email,
                        "accessAll": False,
                        "collections": [],
                    }
                )
            ],
            json={
                "type": 2,
                "accessAll": True,
                "externalId": None,
                "resetPasswordEnrolled": True,
                "object": "member",
                "id": "XXXXXXXX",
                "userId": "YYYYYYYY",
                "name": "John Smith",
                "email": "jsmith@example.com",
                "twoFactorEnabled": True,
                "status": 0,
                "collections": [],
            },
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user_id = client.invite_user(user=UmpUser(username=test_user, email=test_email, roles_by_team={}))

        assert user_id == "XXXXXXXX"


def test_failed_invite() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            body="",
            status=500,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(Exception, match="Failed to invite user"):
            client.invite_user(user=UmpUser(username="test.user", email="test@example.com", roles_by_team={}))


def test_handle_already_invited_user(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            json={
                "data": [
                    {
                        "type": 0,
                        "externalId": "test.user",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "XXXXXXXX",
                        "userId": "YYYYYYYY",
                        "name": "test.user",
                        "email": "test@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [],
                    }
                ]
            },
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            json={"object": "error", "message": "This user has already been invited.", "errors": None},
            status=400,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with caplog.at_level(logging.INFO):
            client.invite_user(user=UmpUser(username="test.user", email="test@example.com", roles_by_team={}))

        assert "User already invited ignoring error" in caplog.text


def test_handle_already_invited_no_matching_email(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            json={
                "data": [
                    {
                        "type": 0,
                        "externalId": "test.user",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "XXXXXXXX",
                        "userId": "YYYYYYYY",
                        "name": "test.user",
                        "email": "test@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [],
                    }
                ]
            },
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            json={"object": "error", "message": "This user has already been invited.", "errors": None},
            status=400,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with caplog.at_level(logging.INFO):
            client.invite_user(user=UmpUser(username="test.user", email="no_match@example.com", roles_by_team={}))

        assert "User already invited ignoring error" in caplog.text


def test_handle_already_invited_http_error(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            json={"object": "error", "message": "The request's model state is invalid."},
            status=400,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            json={"object": "error", "message": "This user has already been invited.", "errors": None},
            status=400,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to retrieve users",
        ):
            client.invite_user(user=UmpUser(username="test.user", email="test@example.com", roles_by_team={}))


def test_failed_login() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://identity.bitwarden.eu/connect/token",
            body="",
            status=500,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to authenticate with " "https://identity.bitwarden.eu/connect/token, " "creds incorrect?",
        ):
            client.invite_user(user=UmpUser(username="test.user", email="test@example.com", roles_by_team={}))


def test_create_group() -> None:
    test_group = "Group Name"
    collection_id = "XXXXXXXX"

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/groups",
            body=b'{"name":"Group Name","accessAll":"false","object":"group","id":"XXXXXXXXX","collections":[]}',
            match=[
                matchers.json_params_matcher(
                    {
                        "name": test_group,
                        "accessAll": False,
                        "externalId": _external_id_base64_encoded(test_group),
                        "collections": [{"id": f"{collection_id}", "readOnly": False}],
                    }
                )
            ],
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        group_id = client.create_group(group_name=test_group, collection_id=collection_id)
        assert group_id == "XXXXXXXXX"


def test_invalid_group_name(caplog: LogCaptureFixture) -> None:
    test_group = ""
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    with caplog.at_level(logging.INFO):
        new_group = client.create_group(group_name=test_group, collection_id="XXXXXXXX")
    assert "Group name invalid" in caplog.text

    assert new_group == ""


def test_failed_to_create_group() -> None:
    test_group = "bad group"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/groups",
            body="",
            status=400,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to create group",
        ):
            client.create_group(group_name=test_group, collection_id="XXXXXX")


def test_get_collections_failure() -> None:
    collection_name = "test_name"
    collection_id = _collection_id(collection_name)
    with responses.RequestsMock() as rsps:
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json=_collection_object_with_base64_encoded_external_id(collection_name),
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get collections",
        ):
            client.update_collection_groups(
                collection_name=collection_name,
                group_id="XXXXXXXX",
                collection_id=collection_id,
            )


def test_get_collection_groups_failure() -> None:
    collection_name = "test_name"
    collection_id = _collection_id(collection_name)
    with responses.RequestsMock() as rsps:
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json={},
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get collection",
        ):
            client.update_collection_groups(
                collection_name=collection_name,
                group_id="XXXXXXXX",
                collection_id=collection_id,
            )


def test_get_user_groups_failure() -> None:
    user_id = "id-test-user01"
    managed_group_ids = ["id-team-one"]
    with responses.RequestsMock() as rsps:
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            json={},
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get user groups",
        ):
            client.associate_user_to_groups(user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=[])


def test_get_groups() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.eu/public/groups",
            json={
                "object": "list",
                "data": [
                    {
                        "name": "team-one",
                        "accessAll": False,
                        "externalId": "team-one",
                        "object": "group",
                        "id": "id-team-one",
                        "collections": [],
                    },
                    {
                        "name": "team-two",
                        "accessAll": False,
                        "externalId": "team-two",
                        "object": "group",
                        "id": "id-team-two",
                        "collections": [],
                    },
                ],
                "continuationToken": "string",
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        assert {"team-one": "id-team-one", "team-two": "id-team-two"} == client.get_groups()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.eu/public/groups",
            json={"error": "error"},
        )

        with pytest.raises(Exception, match="Failed to get groups"):
            client.get_groups()


def test_user_custom_group_ids() -> None:
    existing_group_ids = ["id-managed-team-1", "id-custom-grp-1", "id-custom-grp-2"]
    custom_group_ids = ["id-custom-grp-1", "id-custom-grp-2"]
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    assert ["id-custom-grp-1", "id-custom-grp-2"] == client._user_custom_group_ids(
        existing_user_group_ids=existing_group_ids, custom_group_ids=custom_group_ids
    )


def test_associate_user_to_group_no_custom_group() -> None:
    user_id = "id-test-user01"
    existing_group_ids = ["id-team-two"]
    managed_group_ids = ["id-team-one"]
    custom_group_ids: List[str] = []
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "groupIds": managed_group_ids + custom_group_ids,
                    }
                )
            ],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        client.associate_user_to_groups(
            user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
        )


def test_associate_user_to_group_multiple_custom_groups() -> None:
    user_id = "id-test-user01"
    managed_group_ids = ["id-managed-team-1", "id-managed-team-2"]
    existing_group_ids = ["id-managed-team-1", "id-custom-grp-1", "id-custom-grp-2"]
    custom_group_ids = ["id-custom-grp-1", "id-custom-grp-2", "id-custom-grp-3"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "groupIds": ["id-managed-team-1", "id-managed-team-2", "id-custom-grp-1", "id-custom-grp-2"],
                    }
                )
            ],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        client.associate_user_to_groups(
            user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
        )


def test_failed_to_associate_user_to_groups() -> None:
    user_id = "id-test-user01"
    existing_group_ids = ["id-team-one"]
    managed_group_ids = ["id-team-two"]
    custom_group_ids: List[str] = []
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "groupIds": managed_group_ids + custom_group_ids,
                    }
                )
            ],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to associate user to group-ids",
        ):
            client.associate_user_to_groups(
                user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
            )


def test_failed_to_get_group_data_to_associate_user_to_groups() -> None:
    user_id = "id-test-user01"
    existing_group_ids = ["id-team-one"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{user_id}/group-ids",
            json=existing_group_ids,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get user groups",
        ):
            client.associate_user_to_groups(user_id=user_id, managed_group_ids=[], custom_group_ids=[])


def test_update_manually_created_collection_group() -> None:
    collection_name = "Team Name One"
    collection_id = _collection_id(collection_name)
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json={
                "externalId": "",
                "object": "collection",
                "id": collection_id,
                "groups": [],
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.update_collection_groups(
            collection_name=collection_name,
            collection_id=collection_id,
            group_id="XXXXXXXX",
        )


def test_get_collection_external_id() -> None:
    collection_name = "Team One"
    collection_id = _collection_id(collection_name)
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json={
                "externalId": "Team Name One",
                "object": "collection",
                "id": collection_id,
                "groups": [],
            },
        )

        assert "Team Name One" == client._BitwardenPublicApi__get_collection_external_id(collection_id)  # type: ignore

        rsps.add(
            status=500,
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json={
                "error": "Failed to get collections",
            },
        )

        with pytest.raises(Exception, match="Failed to get collections"):
            client._BitwardenPublicApi__get_collection_external_id(collection_id)  # type: ignore


def test_failed_to_update_collection_group() -> None:
    collection_name = "Team Name One"
    collection_id = _collection_id(collection_name)
    group_id = "ZZZZZZZZ"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json=_collection_object_with_base64_encoded_external_id(collection_name),
        )
        rsps.add(
            status=400,
            content_type="application/json",
            method="PUT",
            url=f"https://api.bitwarden.eu/public/collections/{collection_id}",
            json={
                "error": "Failed to update the collection groups",
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to update the collection groups",
        ):
            client.update_collection_groups(
                collection_name=collection_name,
                collection_id=collection_id,
                group_id=group_id,
            )


def test_list_existing_collections() -> None:
    team_one_name = "Team One"
    teams = [team_one_name]
    team_name_one_external_id = _external_id_base64_encoded(team_one_name)
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id(
                        team_one_name, groups=[{"id": "YYYYYYYY", "readOnly": True}]
                    ),
                ]
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        collections = client.list_existing_collections(teams)

        assert collections == {"Team One": {"id": "id-team-one", "externalId": team_name_one_external_id}}


def test_update_collection_groups_success() -> None:
    collection_name = "Test Collection"
    collection_id = _collection_id(collection_name)

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            f"https://api.bitwarden.eu/public/collections/{collection_id}",
            status=200,
            json=_collection_object_with_base64_encoded_external_id(collection_name),
        )
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/collections/{collection_id}",
            status=200,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        client.update_collection_groups(
            collection_name=collection_name,
            collection_id=collection_id,
            group_id="XXXXXXXX",
        )

        assert len(rsps.calls) == 4
        assert rsps.calls[-1].request.method == "PUT"
        assert rsps.calls[-1].request.url == f"https://api.bitwarden.eu/public/collections/{collection_id}"


def test_list_existing_collections_duplicate() -> None:
    team_one_name = "Team Name One"
    teams = [team_one_name]
    team_one_external_id = _external_id_base64_encoded(team_one_name)
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id(
                        team_one_name, groups=[{"id": "YYYYYYYY", "readOnly": True}]
                    ),
                    _collection_object_with_base64_encoded_external_id(
                        team_one_name, groups=[{"id": "YYYYYYYY", "readOnly": True}]
                    ),
                ]
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        collections = client.list_existing_collections(teams)

        assert collections == {"Team Name One": {"id": "duplicate", "externalId": team_one_external_id}}


def test_no_matching_collections() -> None:
    teams = ["Team Name One", "Team Name Two"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url="https://api.bitwarden.eu/public/collections",
            json={
                "data": [
                    {
                        "externalId": "Group Name",
                        "object": "collection",
                        "id": "XXXXXXXX",
                        "groups": [{"id": "YYYYYYYY", "readOnly": True}],
                    }
                ]
            },
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        collections = client.list_existing_collections(teams)

        assert collections == {}


def test_fail_to_list_collections() -> None:
    teams = ["Team Name One", "Team Name Two"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url="https://api.bitwarden.eu/public/collections",
            json={},
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to list collections",
        ):
            client.list_existing_collections(teams)


def test_list_existing_groups() -> None:
    teams = ["Team Name One", "Team Name Two"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups",
            json={
                "object": "list",
                "data": [
                    {
                        "object": "group",
                        "id": "YYYYYYYY",
                        "collections": [],
                        "name": "Team Name One",
                        "accessAll": False,
                        "externalId": None,
                    }
                ],
            },
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        successful_response = client.list_existing_groups(users_teams=teams)

        assert successful_response == {teams[0]: "YYYYYYYY"}


def test_list_existing_groups_with_duplicates() -> None:
    teams = ["Team Name One", "Team Name Two"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups",
            json={
                "object": "list",
                "data": [
                    {
                        "object": "group",
                        "id": "YYYYYYYY",
                        "collections": [],
                        "name": "Team Name One",
                        "accessAll": False,
                        "externalId": None,
                    },
                    {
                        "object": "group",
                        "id": "XXXXXXX",
                        "collections": [],
                        "name": "Team Name One",
                        "accessAll": False,
                        "externalId": None,
                    },
                ],
            },
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        successful_response = client.list_existing_groups(users_teams=teams)

        assert successful_response == {teams[0]: "duplicate"}


@responses.activate
def test_failed_to_list_groups() -> None:
    teams = ["Team Name One", "Team Name Two"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups",
            body="",
            status=400,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to list groups",
        ):
            client.list_existing_groups(users_teams=teams)


def test_collate_user_group_ids() -> None:
    team_one_name = "Team One"
    team_two_name = "Team Two"
    team_one_external_id = _external_id_base64_encoded(team_one_name)
    teams = [team_one_name, team_two_name]
    groups = {team_two_name: "WWWWWWWW"}
    collections = {
        team_one_name: {"id": _collection_id(team_one_name), "externalID": ""},
        team_two_name: {"id": _collection_id(team_two_name), "externalID": ""},
    }
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{_collection_id(team_one_name)}",
            json=_collection_object_with_base64_encoded_external_id(team_one_name),
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/collections/{_collection_id(team_two_name)}",
            json=_collection_object_with_base64_encoded_external_id(
                team_two_name, groups=[{"id": "WWWWWWWW", "readOnly": False}]
            ),
        )
        rsps.add(
            method=responses.PUT,
            url=f"https://api.bitwarden.eu/public/collections/{_collection_id(team_one_name)}",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "externalId": team_one_external_id,
                        "groups": [{"id": "YYYYYYYY", "readOnly": False}],
                    }
                )
            ],
            status=200,
            content_type="application/json",
        )

        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/groups",
            json={
                "name": team_one_name,
                "externalId": team_one_name,
                "accessAll": False,
                "object": "group",
                "id": "YYYYYYYY",
                "collections": [{"id": _collection_id(team_one_name), "readOnly": False}],
            },
            match=[
                matchers.json_params_matcher(
                    {
                        "name": team_one_name,
                        "accessAll": False,
                        "externalId": team_one_external_id,
                        "collections": [{"id": _collection_id(team_one_name), "readOnly": False}],
                    }
                )
            ],
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        successful_response = client.collate_user_group_ids(teams=teams, groups=groups, collections=collections)

        assert successful_response == ["YYYYYYYY", "WWWWWWWW"]


def test_collate_user_group_ids_duplicates() -> None:
    teams = ["Team Name One"]
    groups = {"Team Name One": "duplicate"}
    collections = {"Team Name One": {"id": "ZZZZZZZZ", "externalID": ""}}
    with responses.RequestsMock(assert_all_requests_are_fired=True):
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="There are duplicate groups or collections",
        ):
            client.collate_user_group_ids(teams=teams, groups=groups, collections=collections)


def test_remove_user(caplog: LogCaptureFixture) -> None:
    username = "test.user02"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.DELETE,
            "https://api.bitwarden.eu/public/members/22222222",
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with caplog.at_level(logging.INFO):
            client.remove_user(
                username=username,
            )

        rsps.assert_call_count("https://api.bitwarden.eu/public/members/22222222", 1) is True
        assert f"User {username} has been removed from the Bitwarden organisation" in caplog.text


def test_remove_user_no_longer_in_org(caplog: LogCaptureFixture) -> None:
    username = "unknown.user"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body='{"data": []}',
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with caplog.at_level(logging.INFO):
            client.remove_user(
                username=username,
            )

        assert f"User {username} not found in the Bitwarden organisation" in caplog.text


def test_remove_user_with_failure(caplog: LogCaptureFixture) -> None:
    username = "test.user02"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.DELETE,
            "https://api.bitwarden.eu/public/members/22222222",
            status=500,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with pytest.raises(Exception, match=f"Failed to delete user {username}"):
            client.remove_user(
                username=username,
            )


def test_get_users(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.get_users()


def test_get_user_by_can_get_user() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        user = client.get_user_by(field="externalId", value="test.user01")

        assert user.get("externalId", "") == "test.user01"
        assert user.get("email", "") == "test.user01@example.com"


def test_get_user_by_can_fail_to_get_user() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(BitwardenUserNotFoundException, match="No user with email idontexist found"):
            client.get_user_by(field="email", value="idontexist")


def test_get_users_failure(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=b'{"object":"error","message":"The request\'s model state is invalid."}',
            status=400,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with pytest.raises(Exception, match="Failed to retrieve users"):
            client.get_users()


def test_get_pending_users(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open(
                os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "resources", "get_members.json")
            ).read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        assert client.get_pending_users()[0].get("name") == "test user03"


def test_reinvite_user(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members/22222222/reinvite",
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.reinvite_user(id="22222222", username="test.user02")


def test_reinvite_user_failed(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members/22222222/reinvite",
            status=500,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with pytest.raises(Exception, match="Failed to reinvite test.user02"):
            client.reinvite_user(id="22222222", username="test.user02")


def test_get_group_id_by_name() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups/",
            json={
                "object": "list",
                "data": [
                    {
                        "name": "Development Team",
                        "externalId": "external_id_123456",
                        "object": "group",
                        "id": "539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "collections": [
                            {
                                "id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09",
                                "readOnly": True,
                                "hidePasswords": True,
                                "manage": True,
                            }
                        ],
                    }
                ],
            },
            status=200,
            content_type="application/json",
        )
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        assert client.get_group_id_by_name("Development Team") == "539a36c5-e0d2-4cf9-979e-51ecf5cf6593"


def test_get_group_id_by_name_not_found() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups/",
            json={"object": "list", "data": [{}]},
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        group_id = client.get_group_id_by_name("Non-existent Group")

    assert group_id == ""


def test_get_group_id_by_name_failure() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups/",
            body=b'{"object":"error","message":"The request\'s model state is invalid."}',
            status=400,
            content_type="application/json",
        )
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with pytest.raises(Exception, match="Failed to retrieve groups"):
            client.get_group_id_by_name("Development Team")


def test_get_users_in_group() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups/539a36c5-e0d2-4cf9-979e-51ecf5cf6593/member-ids",
            json=["11111111"],
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        assert client.get_users_in_group("539a36c5-e0d2-4cf9-979e-51ecf5cf6593") == ["11111111"]


def test_get_users_in_group_failure() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/groups/539a36c5-e0d2-4cf9-979e-51ecf5cf6593/member-ids",
            body=b'{"object":"error","message":"The request\'s model state is invalid."}',
            status=400,
            content_type="application/json",
        )
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with pytest.raises(Exception, match="Failed to get users in group"):
            client.get_users_in_group("539a36c5-e0d2-4cf9-979e-51ecf5cf6593")


def test_get_users_in_group_with_empty(caplog: LogCaptureFixture) -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    with caplog.at_level(logging.INFO):
        client.get_users_in_group("")

    assert "group_id cannot be empty" in caplog.text


def test_get_users_by_group_name() -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )
    with (
        patch.object(client, "get_group_id_by_name", return_value="group_id") as mock_get_group_id_by_name,
        patch.object(client, "get_users_in_group", return_value=["user_id"]) as get_mock_users_in_group,
    ):
        users = client.get_users_by_group_name("Development Team")

    assert mock_get_group_id_by_name.call_count == 1
    assert get_mock_users_in_group.call_count == 1
    assert users == ["user_id"]


def test_get_users_by_empty_group(caplog: LogCaptureFixture) -> None:
    client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )
    with (
        caplog.at_level(logging.INFO),
        patch.object(client, "get_group_id_by_name", return_value=[]) as mock_get_group_id,
    ):
        users = client.get_users_by_group_name("Development Team")

    assert "Group Development Team not found" in caplog.text
    assert mock_get_group_id.call_count == 1
    assert users == []


# Helper functions


def _external_id_base64_encoded(id: str) -> str:
    return base64.b64encode(id.encode()).decode("utf-8")


def _collection_id(name: str) -> str:
    return f"id-{name.replace(' ', '-').lower()}"


def _collection_object_with_base64_encoded_external_id(name: str, groups: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    return {
        "externalId": _external_id_base64_encoded(name),
        "object": "collection",
        "id": _collection_id(name),
        "groups": groups,
    }


def _collection_object_with_unencoded_external_id(name: str, groups: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    return {
        "externalId": name,
        "object": "collection",
        "id": _collection_id(name),
        "groups": groups,
    }


def _collection_object_with_empty_external_id(name: str, groups: List[Dict[str, Any]] = []) -> Dict[str, Any]:
    return {
        "externalId": "",
        "object": "collection",
        "id": _collection_id(name),
        "groups": groups,
    }


def _user_collection(
    name: str, readOnly: bool = True, hidePasswords: bool = False, manage: bool = False
) -> Dict[str, Any]:
    return {"id": _collection_id(name), "readOnly": readOnly, "hidePasswords": hidePasswords, "manage": manage}
