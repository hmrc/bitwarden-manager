import logging
from typing import Dict, Any, Set
from jsonschema import validate

from requests import HTTPError, get

from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, session

onboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "list_custom_groups",
        },
    },
    "required": ["event_name"],
}

UMP_API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
BITWARDEN_API_URL = "https://api.bitwarden.com/public"
REQUEST_TIMEOUT_SECONDS = 10


def get_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    return logger


logger = get_logger()


class ListCustomGroups:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        user_management_api: UserManagementApi,
    ):
        self.bitwarden_api = bitwarden_api
        self.user_management_api = user_management_api

    def get_ump_teams(self) -> Set[str]:
        bearer = self.user_management_api._UserManagementApi__fetch_token()  # type: ignore
        response = get(
            f"{UMP_API_URL}/organisations/teams",
            headers={
                "Token": bearer,
                "requester": self.user_management_api._UserManagementApi__client_id,  # type: ignore
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
        return {t.get("team") for t in response_json.get("teams", [])}

    def get_bitwarden_groups(self) -> Set[str]:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        response = session.get(f"{BITWARDEN_API_URL}/groups", timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get bitwarden groups") from error
        response_json: Dict[str, Any] = response.json()
        return {group.get("name") for group in response_json.get("data", [])}

    def bitwarden_groups_not_in_ump(self, bitwarden_groups: Set[str], ump_teams: Set[str]) -> Set[str]:
        return bitwarden_groups - ump_teams

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)
        custom_groups = self.bitwarden_groups_not_in_ump(self.get_bitwarden_groups(), self.get_ump_teams())

        logger.info("List of custom groups:")
        logger.info(custom_groups)
