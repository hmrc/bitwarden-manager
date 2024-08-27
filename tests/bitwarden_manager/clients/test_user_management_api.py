import logging
import time

import pytest
import responses
from requests.exceptions import ConnectTimeout, Timeout
from _pytest.logging import LogCaptureFixture
from urllib.parse import quote

from bitwarden_manager.clients.user_management_api import UserManagementApi, REQUEST_TIMEOUT_SECONDS

API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
AUTH_URL = "https://user-management-auth-production.tools.tax.service.gov.uk/v1/login"


@responses.activate
def test_get_user_teams() -> None:
    test_user = "test.user"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            f"{API_URL}/organisations/users/{test_user}/teams",
            status=200,
            content_type="application/json",
            body=b'{"teams": [{"slack": "https://example.com","team": "Example Team"},'
            b'{"slack": "https://example.com","team": "Example Team Two"}]}',
        )
        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        team_list = client.get_user_teams(username=test_user)

        assert team_list == ["Example Team", "Example Team Two"]


@responses.activate
def test_missing_user(caplog: LogCaptureFixture) -> None:
    missing_user = "missing.user"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            f"{API_URL}/organisations/users/{missing_user}/teams",
            status=404,
            content_type="application/json",
            body=b'{"reason": "Not Found"}',
        )
        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with caplog.at_level(logging.INFO):
            client.get_user_teams(username=missing_user)

        assert "User Not Found" in caplog.text


@responses.activate
def test_failed_to_get_user_teams(caplog: LogCaptureFixture) -> None:
    missing_user = "missing.user"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            f"{API_URL}/organisations/users/{missing_user}/teams",
            status=400,
            content_type="application/json",
            body=b'{"reason": "Bad Request"}',
        )
        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to get teams for user",
        ):
            client.get_user_teams(username=missing_user)


@responses.activate
def test_invalid_user(caplog: LogCaptureFixture) -> None:
    invalid_user = "invalid.user!"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            responses.GET,
            f"{API_URL}/organisations/users/{invalid_user}/teams",
            status=422,
            content_type="application/json",
            body=b'{"reason": "Invalid uid"}',
        )
        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        with caplog.at_level(logging.INFO):
            client.get_user_teams(username=invalid_user)

        assert "Invalid User" in caplog.text


@responses.activate
def test_failed_login() -> None:
    test_user = "test.user"
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            method=responses.POST,
            url=AUTH_URL,
            body=b'{"reason": "Unauthorised"}',
            status=401,
            content_type="application/json",
        )

        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(
            Exception,
            match="Failed to authenticate with " f"{AUTH_URL}, " "creds incorrect?",
        ):
            client.get_user_teams(username=test_user)


def test_get_user_role_by_team() -> None:
    team = "Cloud Security"
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{API_URL}/organisations/teams/{quote(team)}/members",
            json={
                "documentation": "https://docs.hmrc.gov.uk/cloudsec",
                "members": [
                    {
                        "displayName": "John Doe",
                        "familyName": "Doe",
                        "givenName": "John",
                        "organisation": "MDTP",
                        "primaryEmail": "john.doe@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "john.doe",
                    },
                    {
                        "displayName": "Foo Bar",
                        "familyName": "Bar",
                        "givenName": "Foo",
                        "organisation": "MDTP",
                        "primaryEmail": "foo.bar@digital.hmrc.gov.uk",
                        "role": "team_admin",
                        "username": "foo.bar",
                    },
                ],
                "slack": "https://hmrcdigital.slack.com/messages/team-cloudsec",
                "slackNotification": "https://hmrcdigital.slack.com/messages/int-cloudsec-notifications",
                "team": "Cloud Security",
            },
        )

        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        assert "user" == client.get_user_role_by_team("john.doe", team)
        assert "team_admin" == client.get_user_role_by_team("foo.bar", team)

        with pytest.raises(Exception, match=f"fake.user is not a member of {team}"):
            client.get_user_role_by_team("fake.user", team)

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url=f"{API_URL}/organisations/teams/{quote(team)}/members",
            json={"error": "error"},
        )

        with pytest.raises(Exception, match=f"Failed to get team members of {team}"):
            client.get_user_role_by_team("john.doe", team)

@responses.activate
def test_get_user_role_by_team_timeout() -> None:
    team = "fake team"
    user = "fake.user"

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.post(
            url=AUTH_URL,
            status=200,
            json={
                "Token": "TEST_BEARER_TOKEN",
                "uid": "user.name",
            },
        )

        rsps.add(
            content_type="application/json",
            method=responses.GET,
            url=f"{API_URL}/organisations/teams/{quote(team)}/members",
            body=ConnectTimeout(),
        )

        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        with pytest.raises(Exception, match=f"Failed to get team members of {team} for {user} before the timeout"):
            client.get_user_role_by_team(user, team)


def test_get_teams() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{API_URL}/organisations/teams",
            json={
                "teams": [
                    {"team": "team-one", "slack": "https://myorg.slack.com/messages/team-one"},
                    {"team": "team-two", "slack": "https://myorg.slack.com/messages/team-two"},
                    {"team": "team-three", "slack": "https://myorg.slack.com/messages/team-three"},
                    {"team": "team-four"},
                    {"team": "team-five"},
                ]
            },
        )

        client = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        assert ["team-one", "team-two", "team-three", "team-four", "team-five"] == client.get_teams()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url=f"{API_URL}/organisations/teams",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            client.get_teams()


MOCKED_LOGIN = responses.Response(
    method="POST",
    url=AUTH_URL,
    status=200,
    json={
        "Token": "TEST_BEARER_TOKEN",
        "uid": "user.name",
    },
)
