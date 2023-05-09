import pytest
import responses
from responses import matchers

from src.bitwarden_public_api import BitwardenPublicApi


@responses.activate
def test_invite_user():
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
            client_id="foo",
            client_secret="bar",
        )
        client.invite_user(
            username=test_user,
            email=test_email,
        )


@responses.activate
def test_failed_invite():
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.POST,
            "https://api.bitwarden.com/public/members",
            body="",
            status=500,
        )

        client = BitwardenPublicApi(
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(Exception, match="Failed to invite user"):
            client.invite_user(username="test.user", email="test@example.com")


@responses.activate
def test_failed_invite_user():
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://identity.bitwarden.com/connect/token",
            body="",
            status=500,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to authenticate with https://identity.bitwarden.com/connect/token, creds incorrect?",
        ):
            client.invite_user(username="test.user", email="test@example.com")


@responses.activate
def test_failed_login():
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.POST,
            "https://identity.bitwarden.com/connect/token",
            body="",
            status=500,
            content_type="application/json",
        )

        client = BitwardenPublicApi(
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to authenticate with https://identity.bitwarden.com/connect/token, creds incorrect?",
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
