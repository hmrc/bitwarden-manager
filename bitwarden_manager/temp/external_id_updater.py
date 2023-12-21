# To be removed once external id of all existing collections has been updated.
# Note: only team collections are in scope

# get all collections
# get all teams for ump
# base64 encode each team in ump teams
# base64 encode external id
# check each collection external id against list of encoded ump teams
# update any collection with a match

import base64
import binascii
import logging
import os
from typing import Any, Dict, List
from requests import HTTPError, Session, get
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.user_management_api import REQUEST_TIMEOUT_SECONDS, UserManagementApi

UMP_API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
BITWARDEN_API_URL = "https://api.bitwarden.com/public"

session = Session()


class Config:
    def __init__(self) -> None:
        self.__logger = self.get_logger()

    def get_env_var(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            raise Exception(f"Missing env var: {name}")
        return value

    def get_logger(self) -> logging.Logger:
        return logging.getLogger()

    def get_ldap_username(self) -> str:
        return self.get_env_var("LDAP_USERNAME")

    def get_ldap_password(self) -> str:
        return self.get_env_var("LDAP_PASSWORD")

    def get_bitwarden_public_api(self) -> BitwardenPublicApi:
        return BitwardenPublicApi(
            logger=self.__logger,
            client_id=self.get_bitwarden_client_id(),
            client_secret=self.get_bitwarden_client_secret(),
        )

    def get_user_management_api(self) -> UserManagementApi:
        return UserManagementApi(
            logger=self.__logger,
            client_id=self.get_ldap_username(),
            client_secret=self.get_ldap_password(),
        )

    def get_bitwarden_client_id(self) -> str:
        return self.get_env_var("BITWARDEN_CLIENT_ID")

    def get_bitwarden_client_secret(self) -> str:
        return self.get_env_var("BITWARDEN_CLIENT_SECRET")


class CollectionUpdater:
    def __init__(self) -> None:
        self.config = Config()
        self.bitwarden_api = self.config.get_bitwarden_public_api()
        self.user_management_api = self.config.get_user_management_api()
        self.__logger = self.config.get_logger()

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
        return [t.get("team") for t in response_json.get("teams", []) if t.get("slack")]

    def base64_safe_decode(self, text: str) -> str:
        try:
            return base64.b64decode(text).decode("utf-8")
        except (UnicodeDecodeError, binascii.Error):
            return ""

    def collections_with_unencoded_exernal_id(
        self, collections: List[Dict[str, Any]], teams: List[str]
    ) -> List[Dict[str, Any]]:
        return [
            collection
            for collection in collections
            if not self.base64_safe_decode(collection.get("externalId", "")) in teams
        ]

    def run(self) -> None:
        collections = self.bitwarden_api._BitwardenPublicApi__list_collections()  # type: ignore
        teams = self.get_teams()

        for collection in self.collections_with_unencoded_exernal_id(collections, teams):
            collection_id = collection.get("id", "")
            self.bitwarden_api._BitwardenPublicApi__update_collection_external_id(  # type: ignore
                collection_id=collection_id,
                external_id=self.bitwarden_api.external_id_base64_encoded(collection.get("externalId", "")),
            )
            self.__logger.info(f"Updated external id of collection: {collection_id}")


class GroupUpdater:
    def __init__(self) -> None:
        self.config = Config()
        self.bitwarden_api = self.config.get_bitwarden_public_api()
        self.__logger = self.config.get_logger()

    # get all groups
    # encode group name and check if it matches external id
    # update any that does not match
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

    def update_group_external_id(self, group: Dict[str, Any]) -> None:
        group_id = group.get("id")
        group_name = group.get("name")
        response = session.put(
            f"{BITWARDEN_API_URL}/groups/{group_id}",
            json={
                "name": group_name,
                "accessAll": group.get("accessAll"),
                "externalId": self.bitwarden_api.external_id_base64_encoded(group.get("externalId", "")),
                "collections": group.get("collections"),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update external id of group: {group_name}") from error

    def run(self) -> None:
        for group in self.get_groups():
            if not self.has_base64_encoded_external_id(group):
                self.update_group_external_id(group)
