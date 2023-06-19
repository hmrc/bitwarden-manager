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
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        user_management_api: UserManagementApi,
    ):
        self.bitwarden_api = bitwarden_api
        self.user_management_api = user_management_api

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)
        user_team_membership = self.user_management_api.get_user_teams(username=event["username"])
        user_id = self.bitwarden_api.invite_user(
            username=event["username"],
            email=event["email"],
        )
        existing_groups = self.bitwarden_api.list_existing_groups(user_team_membership)
        existing_collections = self.bitwarden_api.list_existing_collections(user_team_membership)
        collections = self.bitwarden_api.list_existing_collections(user_team_membership)
        group_ids = self.bitwarden_api.collate_user_group_ids(
            teams=user_team_membership,
            groups=existing_groups,
        )
        self.bitwarden_api.associate_user_to_groups(
            user_id=user_id,
            group_ids=group_ids,
        )
