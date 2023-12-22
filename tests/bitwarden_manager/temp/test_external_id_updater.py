import base64
import json
import re
from typing import Any, Dict

import pytest
import responses
from responses import matchers

from bitwarden_manager.temp.external_id_updater import CollectionUpdater, Config, GroupUpdater
from tests.bitwarden_manager.clients.test_bitwarden_public_api import (
    _collection_object_with_base64_encoded_external_id,
    _collection_object_with_unencoded_external_id,
)
from tests.bitwarden_manager.clients.test_user_management_api import MOCKED_LOGIN


@pytest.mark.parametrize(
    "env_var_key,config_function",
    [
        ("LDAP_USERNAME", Config().get_ldap_username),
        ("LDAP_PASSWORD", Config().get_ldap_password),
        ("BITWARDEN_CLIENT_ID", Config().get_bitwarden_client_id),
        ("BITWARDEN_CLIENT_SECRET", Config().get_bitwarden_client_secret),
    ],
)
def test_missing_env_vars(env_var_key: str, config_function: Any, monkeypatch: Any) -> None:
    monkeypatch.delenv(env_var_key, raising=False)

    with pytest.raises(Exception) as mce:
        config_function()

    assert re.search(env_var_key, str(mce)) is not None


def test_get_teams() -> None:
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

        assert ["team-one", "team-two", "team-three"] == CollectionUpdater().get_teams()

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://user-management-backend-production.tools.tax.service.gov.uk/v2/organisations/teams",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            CollectionUpdater().get_teams()


def test_update_collection_external_id() -> None:
    team_one_name = "Team One"
    id = "id-team-one"
    external_id_encoded = _external_id_base64_encoded(team_one_name)

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url=f"https://api.bitwarden.com/public/collections/{id}",
            json=_collection_object_with_unencoded_external_id(team_one_name),
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/{id}",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "externalId": external_id_encoded,
                        "groups": [],
                    }
                )
            ],
        )

        CollectionUpdater().update_collection_external_id(id, external_id_encoded)

        rsps.assert_call_count(f"https://api.bitwarden.com/public/collections/{id}", 2) is True
        assert rsps.calls[1].response.status_code == 200
        assert json.loads(rsps.calls[1].request.body) == {"externalId": external_id_encoded, "groups": []}

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/{id}",
            body="",
            match=[
                matchers.json_params_matcher(
                    {
                        "externalId": external_id_encoded,
                        "groups": [],
                    }
                )
            ],
        )

        with pytest.raises(Exception, match=f"Failed to update external id of collection: {id}"):
            CollectionUpdater().update_collection_external_id(id, external_id_encoded)


def test_collections_with_unencoded_external_id() -> None:
    collections = [
        _collection_object_with_base64_encoded_external_id("team-one"),
        _collection_object_with_base64_encoded_external_id("team-two"),
        _collection_object_with_base64_encoded_external_id("team-three"),
        _collection_object_with_unencoded_external_id("team-four"),
        _collection_object_with_unencoded_external_id("team-five"),
    ]
    teams = ["team-one", "team-two", "team-three", "team-four", "team-five"]
    assert [
        _collection_object_with_unencoded_external_id("team-four"),
        _collection_object_with_unencoded_external_id("team-five"),
    ] == CollectionUpdater().collections_with_unencoded_exernal_id(collections, teams)


def test_base64_safe_decode() -> None:
    assert "team-one" == CollectionUpdater().base64_safe_decode("dGVhbS1vbmU=")
    assert "" == CollectionUpdater().base64_safe_decode("un-base64-encoded-text")


def test_collection_updater_run() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(UMP_MOCKED_LOGIN)
        rsps.add(BITWARDEN_MOCKED_LOGIN)
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
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/collections",
            json={
                "data": [
                    _collection_object_with_base64_encoded_external_id("team-one"),
                    _collection_object_with_base64_encoded_external_id("team-two"),
                    _collection_object_with_base64_encoded_external_id("team-three"),
                    _collection_object_with_unencoded_external_id("team-four"),
                ]
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/collections/id-team-four",
            json=_collection_object_with_unencoded_external_id("id-team-four"),
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/collections/id-team-four",
            body="",
            match=[
                matchers.json_params_matcher({"externalId": _external_id_base64_encoded("team-four"), "groups": []})
            ],
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/collections/id-team-four",
            body="",
            match=[
                matchers.json_params_matcher({"externalId": _external_id_base64_encoded("team-four"), "groups": []})
            ],
        )

        CollectionUpdater().run()

        put_calls = [c for c in rsps.calls if c.request.method == "PUT"]
        assert len(put_calls) == 1


def test_get_groups() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
            json={
                "data": [
                    _group_object_with_base64_encoded_external_id("team-one"),
                    _group_object_with_base64_encoded_external_id("team-two"),
                    _group_object_with_base64_encoded_external_id("team-three"),
                ]
            },
        )
        groups = GroupUpdater().get_groups()
        assert [
            _group_object_with_base64_encoded_external_id("team-one"),
            _group_object_with_base64_encoded_external_id("team-two"),
            _group_object_with_base64_encoded_external_id("team-three"),
        ] == groups

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            GroupUpdater().get_groups()


def test_update_group_external_id() -> None:
    group_name = "team-one"
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/groups/id-team-one",
            match=[
                matchers.json_params_matcher(
                    {
                        "name": group_name,
                        "accessAll": True,
                        "externalId": _external_id_base64_encoded(group_name),
                        "collections": [],
                    }
                )
            ],
        )
        GroupUpdater().update_group_external_id(group=_group_object_with_unencoded_external_id(group_name))
        assert rsps.calls[0].response.status_code == 200

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/groups/id-team-one",
            match=[
                matchers.json_params_matcher(
                    {
                        "name": group_name,
                        "accessAll": True,
                        "externalId": _external_id_base64_encoded(group_name),
                        "collections": [],
                    }
                )
            ],
        )

        with pytest.raises(Exception):
            GroupUpdater().update_group_external_id(group=_group_object_with_unencoded_external_id(group_name))


def test_GroupUpdater_run() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.GET,
            url="https://api.bitwarden.com/public/groups",
            json={
                "data": [
                    _group_object_with_base64_encoded_external_id("team-one"),
                    _group_object_with_base64_encoded_external_id("team-two"),
                    _group_object_with_base64_encoded_external_id("team-three"),
                    _group_object_with_unencoded_external_id("team-four"),
                ]
            },
        )
        rsps.add(
            status=200,
            content_type="application/json",
            method=responses.PUT,
            url="https://api.bitwarden.com/public/groups/id-team-four",
            match=[
                matchers.json_params_matcher(
                    {
                        "name": "team-four",
                        "accessAll": True,
                        "externalId": _external_id_base64_encoded("team-four"),
                        "collections": [],
                    }
                )
            ],
        )
        GroupUpdater().run()
        assert rsps.calls[-1].response.status_code == 200
        assert json.loads(rsps.calls[-1].response.request.body) == {
            "name": "team-four",
            "accessAll": True,
            "externalId": "dGVhbS1mb3Vy",
            "collections": [],
        }


def test_has_base64_encoded_external_id() -> None:
    assert (
        GroupUpdater().has_base64_encoded_external_id(_group_object_with_base64_encoded_external_id("team-one")) is True
    )
    assert GroupUpdater().has_base64_encoded_external_id(_group_object_with_unencoded_external_id("team-one")) is False


# Helper functions


def _external_id_base64_encoded(id: str) -> str:
    return base64.b64encode(id.encode()).decode("utf-8")


def _id(name: str) -> str:
    return f"id-{name.replace(' ', '-').lower()}"


def _group_object_with_base64_encoded_external_id(name: str) -> Dict[str, Any]:
    return {
        "name": name,
        "accessAll": True,
        "externalId": _external_id_base64_encoded(name),
        "object": "group",
        "id": _id(name),
        "collections": [],
    }


def _group_object_with_unencoded_external_id(name: str) -> Dict[str, Any]:
    return {"name": name, "accessAll": True, "externalId": name, "object": "group", "id": _id(name), "collections": []}


@pytest.fixture(autouse=True)
def _setup_environment(monkeypatch: Any) -> None:
    env_vars = {
        "BITWARDEN_CLIENT_ID": "the-bitwarden-client-id",
        "BITWARDEN_CLIENT_SECRET": "the-bitwarden-client-secret",
        "LDAP_USERNAME": "the-ldap-username",
        "LDAP_PASSWORD": "the-ldap-password",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

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