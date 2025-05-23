import logging
import os
import responses
import json


from bitwarden_manager.get_user_details import GetUserDetails
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

fake_good_event = {
    "resource": "/bitwarden-manager/users",
    "path": "/bitwarden-manager/users",
    "httpMethod": "GET",
    "queryStringParameters": {"username": "test.user01"},
}

fake_bad_event = {
    "resource": "/bitwarden-manager/users",
    "path": "/bitwarden-manager/users",
    "httpMethod": "GET",
    "queryStringParameters": {"username": "no.such-user"},
}

MOCKED_GET_MEMBERS = responses.Response(
    status=200,
    content_type="application/json",
    method=responses.GET,
    url="https://api.bitwarden.eu/public/members",
    body=open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "get_members.json")).read(),
)

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


def test_get_user_details() -> None:
    username = "test.user01"
    api_client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        response = GetUserDetails(api_client).run(event=fake_good_event)

        assert username in response["body"]
        assert "ADMIN" in response["body"]


def test_get_user() -> None:
    username = "test.user01"
    api_client = BitwardenPublicApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        get_user_details = GetUserDetails(bitwarden_api=api_client)

        user = get_user_details.get_user(username=username)
        assert username in user["body"]
        assert "CONFIRMED" in user["body"]

        user = get_user_details.get_user(username="doesnot.exist")
        assert user["body"] == json.dumps({"ERROR": "Username doesnot.exist not found"})
