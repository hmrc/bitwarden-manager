from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

from bitwarden_manager.clients.user_management_api import UserManagementApi
onboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {"type": "string", "description": "name of the current event", "pattern": "new_user"},
        "username": {"type": "string", "description": "the users ldap username"},
        "email": {"type": "string", "pattern": "^(.+)@(.+)$", "description": "The users full work email address"},
    },
    "required": ["event_name", "username", "email"],
}


class OnboardUser:
    def __init__(self, bitwarden_api: BitwardenPublicApi):
        user_management_api: UserManagementApi,
        self.bitwarden_api = bitwarden_api

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)
        user_team_membership = self.user_management_api.get_user_teams(username=event["username"])
            username=event["username"],
            email=event["email"],
        )
