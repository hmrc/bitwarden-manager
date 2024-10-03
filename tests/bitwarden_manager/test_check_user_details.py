import logging
import pytest
import responses
import pathlib


from bitwarden_manager.check_user_details import CheckUserDetails
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient

fake_good_event = {
    "resource": "/bitwarden-manager/check-user",
    "path": "/bitwarden-manager/check-user",
    "httpMethod": "GET",
    "queryStringParameters": {"username": "test.user01"},
}
fake_bad_event = {
    "resource": "/bitwarden-manager/check-user",
    "path": "/bitwarden-manager/check-user",
    "httpMethod": "GET",
    "queryStringParameters": {"username": "no.such-user"},
}

MOCKED_GET_MEMBERS = responses.Response(
    status=200,
    content_type="application/json",
    method=responses.GET,
    url="https://api.bitwarden.eu/public/members",
    body=open("tests/bitwarden_manager/resources/get_members.json").read(),
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


def test_get_user_by_username() -> None:
    username = "test.user01"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        user = client.get_user_by_username(username=username)

        assert username in user["email"]
        assert "11111111" == user["id"]

        with pytest.raises(Exception, match=r"No user with username .* found"):
            client.get_user_by_username(username="does.not.exist")


def test_check_user_details() -> None:
    username = "test.user01"

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(MOCKED_GET_MEMBERS)
        api_client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        vault_client = BitwardenVaultClient(
            cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./stubs/bitwarden_client_stub.py")),
            client_id="foo",
            client_secret="bar",
            export_enc_password="hmrc2023",
            logger=logging.getLogger(),
            organisation_id="abc-123",
            password="very secure pa$$w0rd!",
            cli_timeout=20,
        )
        response = CheckUserDetails(api_client, vault_client).run(event=fake_good_event)

        assert username in response["email"]
        assert "11111111" == response["id"]

        with pytest.raises(Exception, match=r"No user with username .* found"):
            CheckUserDetails(api_client, vault_client).run(event=fake_bad_event)
