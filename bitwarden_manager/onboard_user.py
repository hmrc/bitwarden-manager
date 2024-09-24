from typing import Dict, Any
from jsonschema import validate
from datetime import datetime

from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
import bitwarden_manager.groups_and_collections as GroupsAndCollections
from bitwarden_manager.user import UmpUser

onboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "const": "new_user",
        },
        "username": {"type": "string", "description": "the users ldap username"},
        "email": {
            "type": "string",
            "pattern": "^(.+)@(.+)$",
            "description": "The users full work email address",
        },
        "service_name": {
            "type": "string",
            "description": "name of the service which invoked the event",
            "enum": ["all", "bitwarden"],
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
        dynamodb_client: DynamodbClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.user_management_api = user_management_api
        self.bitwarden_vault_client = bitwarden_vault_client
        self.dynamodb_client = dynamodb_client

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)
        teams = self.user_management_api.get_user_teams(username=event["username"])
        roles_by_team = {
            team: self.user_management_api.get_user_role_by_team(event["username"], team=team) for team in teams
        }

        user = UmpUser(username=event["username"], email=event["email"], roles_by_team=roles_by_team)
        user_id = self.bitwarden_api.invite_user(user=user)
        date = datetime.today().strftime("%Y-%m-%d")

        record = self.dynamodb_client.get_item_from_table(table_name="bitwarden", key={"username": user.username})
        if record:
            self.dynamodb_client.delete_item_from_table(table_name="bitwarden", key={"username": user.username})

        self.dynamodb_client.write_item_to_table(
            table_name="bitwarden", item={"username": user.username, "invite_date": date, "reinvites": 0}
        )

        existing_groups = self.bitwarden_api.list_existing_groups(teams)
        existing_collections = self.bitwarden_api.list_existing_collections(teams)
        self.bitwarden_vault_client.create_collections(
            GroupsAndCollections.missing_collection_names(teams, existing_collections)
        )

        collections = self.bitwarden_api.list_existing_collections(teams)
        managed_group_ids = self.bitwarden_api.collate_user_group_ids(
            teams=teams,
            groups=existing_groups,
            collections=collections,
        )

        custom_group_ids = GroupsAndCollections.non_ump_based_group_ids(
            groups=self.bitwarden_api.get_groups(), teams=self.user_management_api.get_teams()
        )

        self.bitwarden_api.associate_user_to_groups(
            user_id=user_id, managed_group_ids=managed_group_ids, custom_group_ids=custom_group_ids
        )

        self.bitwarden_api.grant_can_manage_permission_to_team_collections(user=user, teams=teams)
