import pytest
import responses
import logging
from unittest import mock
from unittest.mock import Mock

from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_public_api import UserType
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.temp.role_updater import UmpApi, BitwardenApi, MemberRoleUpdater
from tests.bitwarden_manager.clients.test_user_management_api import MOCKED_LOGIN


@pytest.fixture
def ump() -> UserManagementApi:
    return UserManagementApi(
        logger=logging.getLogger(),
        client_id="foo",
        client_secret="bar",
    )


def test_get_teams(ump: UserManagementApi) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams",
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

        assert ["team-one", "team-two", "team-three", "team-four", "team-five"] == UmpApi(ump).get_teams()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            UmpApi(ump).get_teams()


def test_get_team_admin_users(ump: UserManagementApi) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        base_url = "https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams"
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{base_url}/team-one/members",
            json={
                "members": [
                    {
                        "displayName": "Felicity Lemon",
                        "familyName": "Lemon",
                        "github": "https://github.com/misslemon",
                        "givenName": "Felicity",
                        "organisation": "MDTP",
                        "primaryEmail": "felicity.lemon@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "felicity.lemon",
                    },
                    {
                        "displayName": "Hercule Poirot",
                        "familyName": "Poirot",
                        "github": "https://github.com/hpoirot",
                        "givenName": "Hercule",
                        "organisation": "MDTP",
                        "primaryEmail": "hercule.poirot@digital.hmrc.gov.uk",
                        "role": "team_admin",
                        "username": "hercule.poirot",
                    },
                    {
                        "displayName": "Arthur Hastings",
                        "familyName": "Hastings",
                        "github": "https://github.com/captainhastings",
                        "givenName": "Arthur",
                        "organisation": "MDTP",
                        "primaryEmail": "arthur.hastings@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "arthur.hastings",
                    },
                ]
            },
        )

        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{base_url}/team-two/members",
            json={
                "members": [
                    {
                        "displayName": "Martha Hudson",
                        "familyName": "Hudson",
                        "github": "https://github.com/mhudson",
                        "givenName": "Martha",
                        "organisation": "MDTP",
                        "primaryEmail": "martha.hudson@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "martha.hudson",
                    },
                    {
                        "displayName": "Sherlock Holmes",
                        "familyName": "Holmes",
                        "github": "https://github.com/sholmes",
                        "givenName": "Sherlock",
                        "organisation": "MDTP",
                        "primaryEmail": "sherlock.holmes@digital.hmrc.gov.uk",
                        "role": "team_admin",
                        "username": "sherlock.holmes",
                    },
                    {
                        "displayName": "John Watson",
                        "familyName": "Hastings",
                        "github": "https://github.com/drwatson",
                        "givenName": "John",
                        "organisation": "MDTP",
                        "primaryEmail": "john.watson@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "john.watson",
                    },
                ]
            },
        )

        assert ["hercule.poirot", "sherlock.holmes"] == UmpApi(ump).get_team_admin_users(["team-one", "team-two"])

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url=f"{base_url}/team-one/members",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            UmpApi(ump).get_team_admin_users(["team-one", "team-two"])


def test_get_bitwarden_members() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(BITWARDEN_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/members",
            json={
                "object": "list",
                "data": [
                    {
                        "type": 2,
                        "accessAll": True,
                        "externalId": "sherlock.holmes",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "48b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Sherlock Holmes",
                        "email": "sherlock.holmes@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                    {
                        "type": 1,
                        "accessAll": True,
                        "externalId": "external_id_123456",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "639a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "58b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Hercule Poirot",
                        "email": "hercule.poirot@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                    {
                        "type": 2,
                        "accessAll": True,
                        "externalId": "external_id_123456",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "739a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "68b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Arthur Hastings",
                        "email": "arthur.hastings@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                ],
            },
        )
        team_admin_users = ["hercule.poirot", "sherlock.holmes"]

        expected = [
            {
                "type": 2,
                "accessAll": True,
                "externalId": "sherlock.holmes",
                "resetPasswordEnrolled": True,
                "object": "member",
                "id": "539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                "userId": "48b47ee1-493e-4c67-aef7-014996c40eca",
                "name": "Sherlock Holmes",
                "email": "sherlock.holmes@example.com",
                "twoFactorEnabled": True,
                "status": 0,
                "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
            }
        ]

        assert expected == BitwardenApi().get_members_to_update(team_admin_users)

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/members",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            BitwardenApi().get_members_to_update(team_admin_users)


def test_update_member_role() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        member_to_update = {
            "type": 2,
            "accessAll": True,
            "externalId": "sherlock.holmes",
            "resetPasswordEnrolled": True,
            "object": "member",
            "id": "539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
            "userId": "48b47ee1-493e-4c67-aef7-014996c40eca",
            "name": "Sherlock Holmes",
            "email": "sherlock.holmes@example.com",
            "twoFactorEnabled": True,
            "status": 0,
            "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
        }

        rsps.add(BITWARDEN_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/members/539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
            json={
                "type": UserType.MANAGER,
                "accessAll": True,
                "externalId": "sherlock.holmes",
                "resetPasswordEnrolled": True,
                "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
            },
        )
        BitwardenApi().update_member_role(member_to_update)
        put_calls = [c for c in rsps.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/members/539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            BitwardenApi().update_member_role(member_to_update)


def test_member_role_updater_run(ump: UserManagementApi) -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        base_url = "https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams"
        rsps.add(UMP_MOCKED_LOGIN)
        rsps.add(BITWARDEN_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=base_url,
            json={
                "teams": [
                    {"team": "team-one", "slack": "https://myorg.slack.com/messages/team-one"},
                    {"team": "team-two", "slack": "https://myorg.slack.com/messages/team-two"},
                ]
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{base_url}/team-one/members",
            json={
                "members": [
                    {
                        "displayName": "Felicity Lemon",
                        "familyName": "Lemon",
                        "github": "https://github.com/misslemon",
                        "givenName": "Felicity",
                        "organisation": "MDTP",
                        "primaryEmail": "felicity.lemon@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "felicity.lemon",
                    },
                    {
                        "displayName": "Hercule Poirot",
                        "familyName": "Poirot",
                        "github": "https://github.com/hpoirot",
                        "givenName": "Hercule",
                        "organisation": "MDTP",
                        "primaryEmail": "hercule.poirot@digital.hmrc.gov.uk",
                        "role": "team_admin",
                        "username": "hercule.poirot",
                    },
                    {
                        "displayName": "Arthur Hastings",
                        "familyName": "Hastings",
                        "github": "https://github.com/captainhastings",
                        "givenName": "Arthur",
                        "organisation": "MDTP",
                        "primaryEmail": "arthur.hastings@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "arthur.hastings",
                    },
                ]
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"{base_url}/team-two/members",
            json={
                "members": [
                    {
                        "displayName": "Martha Hudson",
                        "familyName": "Hudson",
                        "github": "https://github.com/mhudson",
                        "givenName": "Martha",
                        "organisation": "MDTP",
                        "primaryEmail": "martha.hudson@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "martha.hudson",
                    },
                    {
                        "displayName": "Sherlock Holmes",
                        "familyName": "Holmes",
                        "github": "https://github.com/sholmes",
                        "givenName": "Sherlock",
                        "organisation": "MDTP",
                        "primaryEmail": "sherlock.holmes@digital.hmrc.gov.uk",
                        "role": "team_admin",
                        "username": "sherlock.holmes",
                    },
                    {
                        "displayName": "John Watson",
                        "familyName": "Hastings",
                        "github": "https://github.com/drwatson",
                        "givenName": "John",
                        "organisation": "MDTP",
                        "primaryEmail": "john.watson@digital.hmrc.gov.uk",
                        "role": "user",
                        "username": "john.watson",
                    },
                ]
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/members",
            json={
                "object": "list",
                "data": [
                    {
                        "type": 2,
                        "accessAll": True,
                        "externalId": "sherlock.holmes",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "48b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Sherlock Holmes",
                        "email": "sherlock.holmes@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                    {
                        "type": 1,
                        "accessAll": True,
                        "externalId": "external_id_123456",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "639a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "58b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Hercule Poirot",
                        "email": "hercule.poirot@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                    {
                        "type": 2,
                        "accessAll": True,
                        "externalId": "external_id_123456",
                        "resetPasswordEnrolled": True,
                        "object": "member",
                        "id": "739a36c5-e0d2-4cf9-979e-51ecf5cf6593",
                        "userId": "68b47ee1-493e-4c67-aef7-014996c40eca",
                        "name": "Arthur Hastings",
                        "email": "arthur.hastings@example.com",
                        "twoFactorEnabled": True,
                        "status": 0,
                        "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
                    },
                ],
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/members/539a36c5-e0d2-4cf9-979e-51ecf5cf6593",
            json={
                "type": UserType.MANAGER,
                "accessAll": True,
                "externalId": "sherlock.holmes",
                "resetPasswordEnrolled": True,
                "collections": [{"id": "bfbc8338-e329-4dc0-b0c9-317c2ebf1a09", "readOnly": True}],
            },
        )

        MemberRoleUpdater(ump).run()

        put_calls = [c for c in rsps.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1


@mock.patch("bitwarden_manager.bitwarden_manager.MemberRoleUpdater")
@mock.patch("bitwarden_manager.redacting_formatter.RedactingFormatter")
@mock.patch("boto3.client")
def test_update_user_roles_event_routing(
    mock_secretsmanager: Mock, mock_log_redacting_formatter: Mock, mock_role_updater: Mock
) -> None:
    event = {
        "event_name": "backfill_user_roles",
    }

    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    mock_role_updater.return_value.run.return_value = None
    mock_log_redacting_formatter.validate_patterns.return_value = None
    BitwardenManager().run(event=event)
    mock_role_updater.return_value.run.assert_called()


UMP_MOCKED_LOGIN = responses.Response(
    method="POST",
    url="https://user-management-auth-production.tools.tax.service.gov.uk/v1/login",
    status=200,
    json={
        "Token": "TEST_BEARER_TOKEN",
        "uid": "user.name",
    },
)

BITWARDEN_MOCKED_LOGIN = responses.Response(
    method="POST",
    url="https://identity.bitwarden.com/connect/token",
    status=200,
    json={
        "access_token": "TEST_BEARER_TOKEN",
        "expires_in": 3600,
        "token_type": "Bearer",
    },
)
