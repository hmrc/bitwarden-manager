import logging

import pytest
import responses
from _pytest.logging import LogCaptureFixture
from responses import matchers

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi


@responses.activate
def test_invite_user() -> None:
    test_user = "test.user"
    test_email = "test@example.com"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.com/public/members",
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
            body="{}",
            status=200,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        client.invite_user(
            username=test_user,
            email=test_email,
        )


@responses.activate
def test_failed_invite() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.com/public/members",
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


@responses.activate
def test_handle_already_invited_user(caplog: LogCaptureFixture) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.com/public/members",
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

        assert "user already invited ignoring error" in caplog.text


@responses.activate
def test_failed_login() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://identity.bitwarden.com/connect/token",
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
            match="Failed to authenticate with " "https://identity.bitwarden.com/connect/token, " "creds incorrect?",
        ):
            client.invite_user(username="test.user", email="test@example.com")


MOCKED_LOGIN = responses.Response(
    method="POST",
    url="https://identity.bitwarden.com/connect/token",
    status=200,
    json={
        "access_token": "TEST_BEARER_TOKEN",
        "expires_in": 3600,
        "token_type": "Bearer",
    },
)
