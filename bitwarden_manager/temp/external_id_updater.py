# To be removed once external id of all existing collections has been updated.
# Note: only team collections are in scope

import base64
import binascii
import logging
import os
from typing import Any, Dict, List

from requests import HTTPError, get
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, session
from bitwarden_manager.clients.user_management_api import UserManagementApi

UMP_API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
BITWARDEN_API_URL = "https://api.bitwarden.com/public"
REQUEST_TIMEOUT_SECONDS = 10


def get_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    return logger


logger = get_logger()


class Config:
    def get_env_var(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise Exception(f"Missing env var: {name}")
        return value

    def get_ldap_username(self) -> str:
        return self.get_env_var("LDAP_USERNAME")

    def get_ldap_password(self) -> str:
        return self.get_env_var("LDAP_PASSWORD")

    def get_bitwarden_public_api(self) -> BitwardenPublicApi:
        return BitwardenPublicApi(
            logger=logger,
            client_id=self.get_bitwarden_client_id(),
            client_secret=self.get_bitwarden_client_secret(),
        )

    def get_user_management_api(self) -> UserManagementApi:
        return UserManagementApi(
            logger=logger,
            client_id=self.get_ldap_username(),
            client_secret=self.get_ldap_password(),
        )

    def get_bitwarden_client_id(self) -> str:
        return self.get_env_var("BITWARDEN_CLIENT_ID")

    def get_bitwarden_client_secret(self) -> str:
        return self.get_env_var("BITWARDEN_CLIENT_SECRET")


class UmpApi:
    def __init__(self) -> None:
        self.config = Config()
        self.user_management_api = self.config.get_user_management_api()

    def get_teams(self) -> List[str]:
        bearer = self.user_management_api._UserManagementApi__fetch_token()  # type: ignore
        response = get(
            f"{UMP_API_URL}/organisations/teams",
            headers={
                "Token": bearer,
                "requester": self.config.get_ldap_username(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception("Failed to get teams", response.content, e) from e
        response_json: Dict[str, Any] = response.json()
        return [t.get("team") for t in response_json.get("teams", [])]


class CollectionUpdater:
    def __init__(self) -> None:
        self.config = Config()
        self.bitwarden_api = self.config.get_bitwarden_public_api()

    def update_collection_external_id(self, collection_id: str, external_id: str) -> None:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        response = session.put(
            f"{BITWARDEN_API_URL}/collections/{collection_id}",
            json={
                "externalId": external_id,
                "groups": self.bitwarden_api._BitwardenPublicApi__get_collection(collection_id).get(  # type: ignore
                    "groups", []
                ),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update external id of collection: {collection_id}") from error

    def base64_safe_decode(self, text: str) -> str:
        try:
            return base64.b64decode(text).decode("utf-8")
        except (UnicodeDecodeError, binascii.Error):
            return ""

    def ump_team_named_collections_with_unencoded_external_id(
        self, collections: List[Dict[str, Any]], teams: List[str]
    ) -> List[Dict[str, Any]]:
        return [
            collection
            for collection in collections
            if collection.get("externalId", "")
            and not self.base64_safe_decode(collection.get("externalId", "")) in teams
            and collection.get("externalId", "") in teams
        ]

    def run(self) -> None:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        collections = self.bitwarden_api._BitwardenPublicApi__list_collections()  # type: ignore
        teams = UmpApi().get_teams()

        for collection in self.ump_team_named_collections_with_unencoded_external_id(collections, teams):
            collection_id = collection.get("id", "")
            external_id = collection.get("externalId", "")
            if external_id:
                self.update_collection_external_id(
                    collection_id=collection_id,
                    external_id=self.bitwarden_api.external_id_base64_encoded(external_id),
                )
                logger.info(f"Updated external id of collection: {collection_id}")

    def setup(self) -> None:  # pragma: no cover
        # For testing only
        collections = [
            {"id": "be5cdb75-d676-463d-89b3-b08a00d54b1e", "externalId": "Platform Security"},
            {"id": "3a092620-ecdf-46ed-ab1a-b0dc00de9d7e", "externalId": "AWS Account Authorisers"},
            {"id": "b2b0a7dc-dac8-4077-9b12-b0dd00c865dd", "externalId": "MDTP Apprentices"},
            {"id": "7cea4408-aa41-469a-a0cb-b08900f6734b", "externalId": "MDTP Platform Pen Testers"},
            {"id": "f4565a6d-88e2-45ea-bb07-b0eb00b588cc", "externalId": "SomeTestCollection"},
            {"id": "c955f5b3-c205-4fc8-b4cd-b0eb00c9f737", "externalId": "PSEC-1962 Manually Created"},
        ]
        # For testing only
        logger.info("Setting up collections with unencoded external id for testing")
        for collection in collections:
            self.update_collection_external_id(collection_id=collection["id"], external_id=collection["externalId"])


class GroupUpdater:
    def __init__(self) -> None:
        self.config = Config()
        self.bitwarden_api = self.config.get_bitwarden_public_api()

    def get_groups(self) -> List[Dict[str, Any]]:
        response = session.get(f"{BITWARDEN_API_URL}/groups")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get groups", response.content, error) from error
        response_json: List[Dict[str, Any]] = response.json().get("data", [])
        return response_json

    def has_base64_encoded_external_id(self, group: Dict[str, Any]) -> bool:
        return group.get("externalId") == self.bitwarden_api.external_id_base64_encoded(group.get("name", ""))

    def is_a_ump_team(self, group: Dict[str, Any], teams: List[str]) -> bool:
        return group.get("name") in teams

    def update_group_external_id(self, group: Dict[str, Any], external_id: str = "") -> None:
        group_id = group.get("id")
        group_name = group.get("name", "")
        group_external_id = external_id
        if len(group_external_id) == 0:
            group_external_id = self.bitwarden_api.external_id_base64_encoded(group_name)

        response = session.put(
            f"{BITWARDEN_API_URL}/groups/{group_id}",
            json={
                "name": group_name,
                "accessAll": group.get("accessAll"),
                "externalId": group_external_id,
                "collections": group.get("collections"),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update external id of group: {group_name}") from error

    def run(self) -> None:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        teams = UmpApi().get_teams()

        for group in self.get_groups():
            if self.is_a_ump_team(group, teams) and not self.has_base64_encoded_external_id(group):
                self.update_group_external_id(group)
                logger.info(f"Updated external id of group {group.get('name')}")

    def setup(self) -> None:  # pragma: no cover
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore

        logger.info("Setting up groups with unencoded external id for testing")

        # For testing only
        teams = [
            "AWS Account Authorisers",
            "Design Resources",
            "MDTP Apprentices",
            "MDTP Platform Pen Testers",
            "WebOps",
            "Platform Security",
            "Telemetry",
            "Test Org admins",
            "Test org non admins",
        ]
        for n in teams:
            for g in self.get_groups():
                if n == g.get("name"):
                    self.update_group_external_id(group=g, external_id=n)


class MemberUpdater:
    def __init__(self) -> None:
        self.config = Config()
        self.bitwarden_api = self.config.get_bitwarden_public_api()

    def get_members(self) -> List[Dict[Any, Any]]:
        response = session.get(f"{BITWARDEN_API_URL}/members")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to retrieve users", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        return response_json["data"]  # type: ignore

    def update_member_external_id(self, details: Dict[str, Any]) -> None:
        member_id = details["id"]
        member_email = details["email"]
        external_id = details["email"].split("@")[0]

        response = session.put(
            f"{BITWARDEN_API_URL}/members/{member_id}",
            json={
                "type": details["type"],
                "accessAll": details["accessAll"],
                "resetPasswordEnrolled": details["resetPasswordEnrolled"],
                "externalId": external_id,
                "email": details["email"],
                "collections": details["collections"],
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update user {member_email}", response.content, error) from error

        logger.info(f"User {member_email} has been updated with the following: {details['email']} {external_id}")

    def run(self) -> None:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        user_data = self.get_members()
        for member in user_data:
            if not member["externalId"]:
                self.update_member_external_id(member)
