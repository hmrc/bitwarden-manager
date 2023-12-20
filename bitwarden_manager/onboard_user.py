from typing import Dict, Any, List

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

from bitwarden_manager.clients.user_management_api import UserManagementApi

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient

onboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "new_user",
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


class OnboardUser:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        user_management_api: UserManagementApi,
        bitwarden_vault_client: BitwardenVaultClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.user_management_api = user_management_api
        self.bitwarden_vault_client = bitwarden_vault_client

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)
        teams = self.user_management_api.get_user_teams(username=event["username"])
        self.bitwarden_api.update_all_team_collection_external_ids(teams)
        user_id = self.bitwarden_api.invite_user(
            username=event["username"],
            email=event["email"],
        )
        existing_groups = self.bitwarden_api.list_existing_groups(teams)
        existing_collections = self.bitwarden_api.list_existing_collections(teams)
        self.bitwarden_vault_client.create_collections(self._missing_collection_names(teams, existing_collections))
        collections = self.bitwarden_api.list_existing_collections(teams)
        group_ids = self.bitwarden_api.collate_user_group_ids(
            teams=teams,
            groups=existing_groups,
            collections=collections,
        )
        self.bitwarden_api.associate_user_to_groups(
            user_id=user_id,
            group_ids=group_ids,
        )

    @staticmethod
    def _missing_collection_names(teams: List[str], existing_collections: Dict[str, Dict[str, str]]) -> List[str]:
        return [team for team in teams if not existing_collections.get(team)]
