from jsonschema import validate
from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.redacting_formatter import get_bitwarden_logger

check_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "path of request",
            "pattern": "/bitwarden-manager/check-user",
        },
        "queryStringParameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "the users ldap username"},
            },
            "required": ["username"],
        },
    },
    "required": ["path"],
}


class CheckUserDetails:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        bitwarden_vault_client: BitwardenVaultClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.bitwarden_vault_client = bitwarden_vault_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        validate(instance=event, schema=check_user_event_schema)

        username = event["queryStringParameters"]["username"]

        self.__logger.info(f"Fetching user details for {username}")
        return self.bitwarden_api.get_user_by_username(username=username)
