import base64
import logging
from typing import Any, Dict, List

import pytest
import responses
from _pytest.logging import LogCaptureFixture
from responses import matchers

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi


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
            body=b'{ "type": 0, "accessAll": true, "externalId": null, "resetPasswordEnrolled": true, "object": '
            b'"member", "id": "XXXXXXXX", "userId": "YYYYYYYY",'
            b'"name": "John Smith", "email": "jsmith@example.com", '
            b'"twoFactorEnabled": true, "status": 0, "collections": [] }',
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user_id = client.invite_user(
            username=test_user,
            email=test_email,
        )

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
            client.invite_user(username="test.user", email="test@example.com")


def test_handle_already_invited_user(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=b'{"data": [ { "type": 0, "accessAll": true, "externalId": "external_id_123456", '
            b'"resetPasswordEnrolled": true, "object": "member", "id": "XXXXXXXX", '
            b'"userId": "YYYYYYYY", "name": "test.user", '
            b'"email": "test@example.com", "twoFactorEnabled": true, "status": 0, "collections": [] } ] }',
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            body=b'{"object":"error","message":"This user has already been invited.","errors":null}',
            status=400,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with caplog.at_level(logging.INFO):
            client.invite_user(username="test.user", email="test@example.com")

        assert "User already invited ignoring error" in caplog.text


def test_handle_already_no_matching_email(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=b'{"data": [ { "type": 0, "accessAll": true, "externalId": "external_id_123456", '
            b'"resetPasswordEnrolled": true, "object": "member", "id": "XXXXXXXX", '
            b'"userId": "YYYYYYYY", "name": "test.user", '
            b'"email": "test@example.com", "twoFactorEnabled": true, "status": 0, "collections": [] } ] }',
            status=200,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            body=b'{"object":"error","message":"This user has already been invited.","errors":null}',
            status=400,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with caplog.at_level(logging.INFO):
            client.invite_user(username="test.user", email="no_match@example.com")

        assert "User already invited ignoring error" in caplog.text


def test_handle_already_invited_http_error(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=b'{"object":"error","message":"The request\'s model state is invalid."}',
            status=400,
            content_type="application/json",
        )
        rsps.add(
            responses.POST,
            "https://api.bitwarden.eu/public/members",
            body=b'{"object":"error","message":"This user has already been invited.","errors":null}',
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
            client.invite_user(username="test.user", email="test@example.com")


def test_failed_login() -> None:
    test_user = "test.user"
    test_email = "test@example.com"
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
            client.invite_user(test_user, test_email)


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
    user_id = "XXXXXXXX"
    group_ids = ["ZZZZZZZZ"]
    with responses.RequestsMock() as rsps:
        rsps.add(MOCKED_LOGIN)
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
            client.associate_user_to_groups(user_id=user_id, group_ids=group_ids)


def test_associate_user_to_group() -> None:
    test_user_id = "XXXXXXXX"
    group_ids = ["ZZZZZZZZ"]
    existing_group_ids = ["YYYYYYYY"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/groups/{group_ids[0]}",
            json={
                "externalId": "Some UMP Id",
                "object": "group",
                "id": group_ids[0],
                "groups": [],
            },
        )
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "groupIds": existing_group_ids + group_ids,
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

        client.associate_user_to_groups(user_id=test_user_id, group_ids=group_ids)


def test_associate_user_to_manually_created_group() -> None:
    test_user_id = "XXXXXXXX"
    group_ids = ["ZZZZZZZZ"]
    existing_group_ids = ["YYYYYYYY"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/groups/{group_ids[0]}",
            json={
                "externalId": None,
                "object": "group",
                "id": group_ids[0],
                "groups": [],
            },
        )
        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        client.associate_user_to_groups(user_id=test_user_id, group_ids=group_ids)


def test_failed_to_associate_user_to_groups() -> None:
    test_user_id = "XXXXXXXX"
    existing_group_ids = ["YYYYYYYY"]
    group_ids = ["ZZZZZZZZ"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/groups/{group_ids[0]}",
            json={
                "externalId": "Some UMP Id",
                "object": "group",
                "id": group_ids[0],
                "groups": [],
            },
        )
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "groupIds": existing_group_ids + group_ids,
                    }
                )
            ],
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
            match="Failed to associate user to group-ids",
        ):
            client.associate_user_to_groups(user_id=test_user_id, group_ids=group_ids)


def test_failed_to_get_group_data_to_associate_user_to_groups() -> None:
    test_user_id = "XXXXXXXX"
    existing_group_ids = ["YYYYYYYY"]
    group_ids = ["ZZZZZZZZ"]
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/members/{test_user_id}/group-ids",
            json=existing_group_ids,
        )
        rsps.add(
            status=400,
            content_type="application/json",
            method="GET",
            url=f"https://api.bitwarden.eu/public/groups/{group_ids[0]}",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get group",
        ):
            client.associate_user_to_groups(user_id=test_user_id, group_ids=group_ids)


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
            body=b'{"object":"list","data":[{"object":"group","id":"YYYYYYYY",'
            b'"collections":[],"name":"Team Name One","accessAll":false,"externalId":null}]}',
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
            body=b'{"object":"list","data":[{"object":"group","id":"YYYYYYYY",'
            b'"collections":[],"name":"Team Name One","accessAll":false,"externalId":null},'
            b'{"object":"group","id":"XXXXXXX","collections":[],'
            b'"name":"Team Name One","accessAll":false,"externalId":null}]}',
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


def test_fetch_user_id_by_email() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user_id = client._BitwardenPublicApi__fetch_user_id(  # type: ignore
            email="test.user01@example.com",
        )
        assert user_id == "11111111"


def test_fetch_user_id_by_external_id() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user_id = client._BitwardenPublicApi__fetch_user_id(  # type: ignore
            external_id="test.user02",
        )

        assert user_id == "22222222"


def test_remove_user(caplog: LogCaptureFixture) -> None:
    username = "test.user02"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            "https://api.bitwarden.eu/public/members",
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
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
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
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
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.get_users()


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
            body=open("tests/bitwarden_manager/resources/get_members.json").read(),
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
