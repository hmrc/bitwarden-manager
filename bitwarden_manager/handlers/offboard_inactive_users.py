from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi

from jsonschema import validate

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
        "inactivity_duration": {"type": "string", "description": "the period a user is considered inactive"},
    },
    "required": ["event_name", "inactivity_duration"],
}

protected_user_emails = [
    "ben.lovatt@digital.hmrc.gov.uk",
    "chris.wright@digital.hmrc.gov.uk",
    "jamie.gibbs@digital.hmrc.gov.uk",
    "marcus.mee@digital.hmrc.gov.uk",
    "nerea.harries@digital.hmrc.gov.uk",
]


class OffboardInactiveUsers:
    def __init__(self, bitwarden_api: BitwardenPublicApi, dry_run: bool = True):
        self.bitwarden_api = bitwarden_api
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])
        self.dry_run = dry_run

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_inactive_users_event_schema)

        self.__logger.info(f"Running activity audit report {event['inactivity_duration']}")
        active_users = self.bitwarden_api.get_active_user_report(event["inactivity_duration"])

        self.__logger.info("Fetching organization members")
        all_users: dict[str, str] = {str(user["id"]): user["email"] for user in self.bitwarden_api.get_users()}

        self.__logger.info("Compiling list of inactive users")
        # Casting: set(all_users) is shorthand for set(all_users.keys())
        inactive_users = set(all_users) - set(active_users)
        self.__logger.info(f"Inactive users: {len(inactive_users)}")

        self.__logger.info("Removing inactive users from bitwarden")
        self.offboard_users(inactive_users, all_users)

    def offboard_users(self, inactive_users: set[str], all_users: dict[str, str]) -> None:
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
            if not self.dry_run and all_users[user_id] not in protected_user_emails:
                self.__logger.info(f"Removing user {all_users[user_id]} from bitwarden")
                self.bitwarden_api.remove_user_by_id(
                    user_id=user_id,
                    username=all_users[user_id],
                )
            else:
                self.__logger.info(f"Skipping offboarding of protected user {all_users[user_id]}")
