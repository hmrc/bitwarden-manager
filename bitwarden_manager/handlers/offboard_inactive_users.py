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
            "pattern": "remove_inactive_users",
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
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
    ):
        self.bitwarden_api = bitwarden_api
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])
        self.dry_run = True

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_inactive_users_event_schema)

        # Get audit activity for active users based on event['inactivity_duration']
        self.__logger.info(f"Running activity audit report {event['inactivity_duration']}")
        active_users = self.get_active_users(event['inactivity_duration'])

        # Get all members of the organization
        self.__logger.info("Fetching organization members")
        all_users = self.get_all_members()

        # Compiling a list of inactive users
        self.__logger.info("Compiling list of inactive users")
        inactive_users = set(all_users) - set(active_users)
        self.__logger.info(f"Inactive users: {len(inactive_users)}")

        # Remove inactive users from Bitwarden
        self.__logger.info(f"Removing inactive users from bitwarden")
        self.offboard_users(inactive_users)

    def get_active_users(self, duration: int) -> set[str]:
        """
        Retrieves a list of active users based on the specified inactivity duration.

        Args:
            duration (int): The period (days) a user is considered inactive.

        Returns:
            set[str]: A list of active user email addresses.
        """
        return self.bitwarden_api.get_active_user_report(duration)

    def get_all_members(self) -> set[str]:
        """
        Retrieves a list of all members of the organization.

        Returns:
            dict[str,str]: A list of all members [id=>email address].
        """
        all_members = self.bitwarden_api.get_users()
        self.__logger.info(f"Found {len(all_members)} members in the organization")
        return {member.get("email", "") for member in all_members}

    def offboard_users(self, inactive_users: set):
        """
        Offboards a list of inactive users from the Bitwarden system.

        We actually need the 'id' of the user.

        This function iterates through a list of inactive users and, for each user,
        executes the necessary processes to remove them from the Bitwarden organization.

        Parameters:
        inactive_users (list): A list containing the ids of the inactive users
                               to be offboarded.

        Returns:
        None
        """
        if self.dry_run:
            self.__logger.info(f"DRY RUN: Would have offboarded {len(inactive_users)} users")
            return

        for user in inactive_users:
            if not self.dry_run and username not in protected_user_emails:
                self.__logger.info(f"Removing user {username} from bitwarden")
                self.bitwarden_api.remove_user_by_id(
                    user_id=user['id'],
                )
            else:
                self.__logger.info(f"Skipping offboarding of protected user {username}")
