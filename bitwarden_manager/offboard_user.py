from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

from bitwarden_manager.redacting_formatter import get_bitwarden_logger

offboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "remove_user",
        },
        "username": {"type": "string", "description": "the users ldap username"},
    },
    "required": ["event_name", "username"],
}


class OffboardUser:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
    ):
        self.bitwarden_api = bitwarden_api
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_user_event_schema)

        self.__logger.info(f"Offboarding user {event['username']}")

        self.__logger.info(f"Removing user {event['username']} from bitwarden")
        self.bitwarden_api.remove_user(
            username=event["username"],
        )
