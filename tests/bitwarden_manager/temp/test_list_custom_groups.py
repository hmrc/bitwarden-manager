import logging
from mock import Mock, patch
import pytest
import responses
from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.temp.list_custom_groups import ListCustomGroups
from tests.bitwarden_manager.clients.test_bitwarden_public_api import MOCKED_LOGIN as BITWARDEN_MOCKED_LOGIN
from tests.bitwarden_manager.clients.test_user_management_api import MOCKED_LOGIN as UMP_MOCKED_LOGIN


def test_get_ump_teams() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(UMP_MOCKED_LOGIN)
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

        ump_api = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        assert {"team-one", "team-two", "team-three", "team-four", "team-five"} == ListCustomGroups(
            bitwarden_api=Mock(), user_management_api=ump_api
        ).get_ump_teams()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            ListCustomGroups(bitwarden_api=Mock(), user_management_api=ump_api).get_ump_teams()


def test_get_bitwarden_groups() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(BITWARDEN_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
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

        bitwarden_api = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        assert {"team-one", "team-two"} == ListCustomGroups(
            bitwarden_api=bitwarden_api, user_management_api=Mock()
        ).get_bitwarden_groups()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            ListCustomGroups(bitwarden_api=bitwarden_api, user_management_api=Mock()).get_bitwarden_groups()


def test_bitwarden_groups_not_in_ump() -> None:
    ump_teams = {"team-one", "team-two"}
    bitwarden_groups = {"team-one", "team-two", "team-three", "team-four"}
    assert {"team-three", "team-four"} == ListCustomGroups(
        bitwarden_api=Mock(), user_management_api=Mock()
    ).bitwarden_groups_not_in_ump(bitwarden_groups=bitwarden_groups, ump_teams=ump_teams)


def test_run(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(UMP_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams",
            json={
                "teams": [
                    {"team": "team-one", "slack": "https://myorg.slack.com/messages/team-one"},
                    {"team": "team-two", "slack": "https://myorg.slack.com/messages/team-two"},
                    {"team": "team-hundred", "slack": "https://myorg.slack.com/messages/team-hundred"},
                ]
            },
        )

        rsps.add(BITWARDEN_MOCKED_LOGIN)
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
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
                    {
                        "name": "team-three",
                        "accessAll": False,
                        "externalId": "team-three",
                        "object": "group",
                        "id": "id-team-three",
                        "collections": [],
                    },
                    {
                        "name": "team-four",
                        "accessAll": False,
                        "externalId": "team-four",
                        "object": "group",
                        "id": "id-team-four",
                        "collections": [],
                    },
                ],
                "continuationToken": "string",
            },
        )

        bitwarden_api = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )
        ump_api = UserManagementApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        ListCustomGroups(bitwarden_api=bitwarden_api, user_management_api=ump_api).run(
            event={"event_name": "list_custom_groups"}
        )
        assert "team-three" in caplog.text
        assert "team-four" in caplog.text


@patch("bitwarden_manager.bitwarden_manager.ListCustomGroups")
@patch("bitwarden_manager.redacting_formatter.RedactingFormatter")
@patch("boto3.client")
def test_list_custom_groups_event_routing(
    mock_secretsmanager: Mock, mock_log_redacting_formatter: Mock, mock_list_custom_groups: Mock
) -> None:
    event = {
        "event_name": "list_custom_groups",
    }

    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    mock_list_custom_groups.return_value.run.return_value = None
    mock_log_redacting_formatter.validate_patterns.return_value = None
    BitwardenManager().run(event=event)
    mock_list_custom_groups.return_value.run.assert_called()
