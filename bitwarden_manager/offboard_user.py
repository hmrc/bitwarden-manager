from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

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
        "email": {
            "type": "string",
            "pattern": "^(.+)@(.+)$",
            "description": "The users full work email address",
        },
    },
    "required": ["event_name", "username", "email"],
}


class OffboardUser:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
    ):
        self.bitwarden_api = bitwarden_api

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_user_event_schema)
        user_id = self.bitwarden_api.remove_user(
            username=event["username"],
            email=event["email"],
        )
