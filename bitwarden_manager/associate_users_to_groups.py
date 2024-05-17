from typing import Dict, Any, List
from jsonschema import validate

from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient

associate_user_to_groups_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "associate_users_to_groups",
        },
    },
    "required": ["event_name"],
}


class AssociateUsersToGroups:
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
        validate(instance=event, schema=associate_user_to_groups_event_schema)
        # breakpoint()
        users = self.bitwarden_api.get_users()
        breakpoint()
        for user in users:
            teams = self.user_management_api.get_user_teams(username=user["external_id"])
            existing_groups = self.bitwarden_api.list_existing_groups(teams)
            existing_collections = self.bitwarden_api.list_existing_collections(teams)
            self.bitwarden_vault_client.create_collections(self._missing_collection_names(teams, existing_collections))
            collections = self.bitwarden_api.list_existing_collections(teams)

            managed_group_ids = self.bitwarden_api.collate_user_group_ids(
                teams=teams,
                groups=existing_groups,
                collections=collections,
            )

            custom_group_ids = self._non_ump_based_group_ids(
                groups=self.bitwarden_api.get_groups(), teams=self.user_management_api.get_teams()
            )

            self.bitwarden_api.associate_user_to_groups(
                user_id=user["id"], managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
            )

    @staticmethod
    def _missing_collection_names(teams: List[str], existing_collections: Dict[str, Dict[str, str]]) -> List[str]:
        return [team for team in teams if not existing_collections.get(team)]

    @staticmethod
    def _non_ump_based_group_ids(groups: Dict[str, str], teams: List[str]) -> List[str]:
        return [id for name, id in groups.items() if name not in teams]
