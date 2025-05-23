from typing import Dict, Any
from jsonschema import validate
from datetime import datetime

from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.clients.bitwarden_public_api import (
    BitwardenPublicApi,
    BitwardenUserAlreadyExistsException,
    BitwardenUserNotFoundException,
)
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
import bitwarden_manager.groups_and_collections as GroupsAndCollections
from bitwarden_manager.redacting_formatter import get_bitwarden_logger
from bitwarden_manager.user import UmpUser

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
        dynamodb_client: DynamodbClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.user_management_api = user_management_api
        self.bitwarden_vault_client = bitwarden_vault_client
        self.dynamodb_client = dynamodb_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=onboard_user_event_schema)

        self.__logger.info(f"Onboarding user {event['username']} to bitwarden")

        try:
            self.__logger.info(f"Checking if user {event['username']} already exists")
            self.bitwarden_api.get_user_by(field="email", value=event["username"])
            self.__logger.info(f"User {event['username']} already exists. Exiting.")
            raise BitwardenUserAlreadyExistsException(f"User {event['username']} already exists.")
        except BitwardenUserNotFoundException:
            self.__logger.info(f"User {event['username']} does not exist. Creating user.")

        self.__logger.info(f"Acquiring teams and roles for user {event['username']}")
        teams = self.user_management_api.get_user_teams(username=event["username"])
        roles_by_team = {
            team: self.user_management_api.get_user_role_by_team(event["username"], team=team) for team in teams
        }

        self.__logger.info(f"Acquiring user {event['username']}'s information from user management")
        user = UmpUser(username=event["username"], email=event["email"], roles_by_team=roles_by_team)

        self.__logger.info(f"Sending bitwarden invite to user {event['username']}'")
        user_id = self.bitwarden_api.invite_user(user=user)
        record = self.dynamodb_client.get_item_from_table(username=user.username)
        if record:
            total_invites = record.get("total_invites", 1) + 1
        else:
            total_invites = 1

        self.__logger.info(f"Adding user {user.username} to dynamodb...")
        self.dynamodb_client.add_item_to_table(
            item={
                "username": user.username,
                "invite_date": datetime.today().strftime("%Y-%m-%d"),
                "reinvites": 0,
                "total_invites": total_invites,
            },
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
        self.bitwarden_api.assign_custom_permissions_to_platsec_user(user=user, teams=teams)
