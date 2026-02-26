from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.redacting_formatter import get_bitwarden_logger

offboard_inactive_users_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "offboard_inactive_users",
        },
        "inactivity_duration": {
            "type": "integer",
            "description": "The number of days a user must be inactive for to be considered for removal",
        },
    },
    "required": ["event_name", "inactivity_duration"],
}


class OffboardInactiveUsers:
    def __init__(
        self, bitwarden_api: BitwardenPublicApi, bitwarden_vault_client: BitwardenVaultClient, dry_run: bool = True
    ):
        self.bitwarden_api = bitwarden_api
        self.bitwarden_vault = bitwarden_vault_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])
        self.dry_run = dry_run

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_inactive_users_event_schema)
        inactivity_duration: int = event["inactivity_duration"]
        self.__logger.info(f"Running activity audit report {inactivity_duration}")
        active_users = self.bitwarden_api.get_active_user_report(inactivity_duration)

        self.__logger.info("Fetching organization members")
        all_users: dict[str, str] = {str(user["id"]): user["email"] for user in self.bitwarden_api.get_users()}
        self.__logger.info(f"Total users: {len(all_users)}")
        # bw_user.get("collections", []))

        self.__logger.info("Compiling list of inactive users")
        # Casting: set(all_users) is shorthand for set(all_users.keys())
        inactive_users = set(all_users) - set(active_users)

        self.__logger.info(f"Active users: {len(active_users)}")
        self.__logger.info(f"Inactive users: {len(inactive_users)}")

        self.__logger.info("Compiling list of protected users")
        protected_users = self._get_protected_users()

        self.__logger.info("Removing inactive users from bitwarden")
        self.offboard_users(inactive_users, all_users, protected_users)

    def offboard_users(self, inactive_users: set[str], all_users: dict[str, str], protected_users: set[str]) -> None:
        """
        Offboards a list of inactive users from the Bitwarden system.

        This function iterates through a list of inactive users and, for each user,
        executes the necessary processes to remove them from the Bitwarden organization.

        Parameters:
        inactive_users (list): A list containing the ids of the inactive users
                               to be offboarded.
        all_users (dict): A dictionary containing the email details of all users in the Bitwarden organization.
        Returns:
        None
        """
        if self.dry_run:
            self.__logger.info(f"DRY RUN: Would have offboarded {len(inactive_users)} users")

        for user_id in inactive_users:
            if not self.dry_run and user_id not in protected_users:
                self.__logger.info(f"Removing user {all_users[user_id]} from bitwarden")
                self.bitwarden_api.remove_user_by_id(
                    user_id=user_id,
                    username=all_users[user_id],
                )
            else:
                reason = "of protected user"
                if user_id not in protected_users:
                    reason = "Dry Run:"
                self.__logger.info(f"Skipping offboarding {reason} {all_users[user_id]}")

    def _get_protected_users(self) -> set[str]:
        # we are looking for all members that have access to the Root collection.
        # also members that are in the MDTP Platform Owners group

        # get the Root collection id
        root_collection_id = self.bitwarden_vault.get_collection_id_by_name("Root")
        self.__logger.info(f"Root collection id: {root_collection_id}")

        users = set()
        for user in self.bitwarden_api.get_users():
            if root_collection_id in user.get("collections", []):
                users.add(user["id"])

        self.__logger.info(f"Root Collection Protected users: {len(users)}")
        # and get all members of the MDTP Platform Owners group
        mdtp_platform_owners_user_ids = self.bitwarden_api.get_users_by_group_name("MDTP Platform Owners")
        self.__logger.info(f"MDTP Platform Owners Protected users: {len(mdtp_platform_owners_user_ids)}")
        return set(users) | set(mdtp_platform_owners_user_ids)
