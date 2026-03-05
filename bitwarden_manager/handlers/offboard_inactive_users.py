from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

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
        "dry_run": {
            "type": "boolean",
            "description": "Report or action the removal of inactive members",
            "default": True,
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

        if event.get("dry_run") is not None:
            self.dry_run = bool(event.get("dry_run"))

        inactivity_duration: int = event["inactivity_duration"]

        self.__logger.info("Fetching organization members")
        members = self.bitwarden_api.get_users()

        self.__logger.info("Fetching events")
        events = self.bitwarden_api.get_events(
            start_date=(datetime.now(timezone.utc) - timedelta(days=event["inactivity_duration"])).strftime("%Y-%m-%d")
        )

        # these aren't all users so numbers may be off after subtraction, but the result it right
        self.__logger.info(f"Compiling list of active members for the last {inactivity_duration} days")
        active_members = self._get_active_member_report(events, members)

        all_members: dict[str, str] = {
            str(member["id"]): member["email"] for member in members if int(member["status"]) == 2
        }

        self.__logger.info("Compiling list of protected members")
        protected_members = self._get_protected_users()

        self.__logger.info("Compiling list of inactive members")
        inactive_members = set(all_members) - set(active_members)

        self.__logger.info(
            f"Total members: {len(all_members)}, Active members: {len(active_members)}, Inactive members: {len(inactive_members)}"  # noqa: E501
        )

        self.__logger.info(f"Removing {len(inactive_members)} inactive members from bitwarden")
        self.offboard_users(inactive_members, all_members, protected_members)

    def offboard_users(self, inactive_users: set[str], all_users: dict[str, str], protected_users: set[str]) -> None:
        if self.dry_run:
            self.__logger.info(f"DRY RUN: Would have offboarded {len(inactive_users)} users")

        for user_id in inactive_users:
            if user_id in protected_users:
                self.__logger.info(f"Skipping protected user {all_users[user_id]}")
                continue

            if self.dry_run:
                self.__logger.info(f"[DRY RUN] Removing user {all_users[user_id]} from bitwarden")

            else:
                self.__logger.info(f"Removing user {all_users[user_id]} from bitwarden")
                self.bitwarden_api.remove_user_by_id(
                    user_id=user_id,
                    username=all_users[user_id],
                )

    def _get_active_member_report(
        self, events: List[Dict[str, Any]] | None = None, members: List[Dict[str, Any]] | None = None
    ) -> set[str]:

        if events is None:
            raise ValueError("The current list of events must be provided")

        if members is None:
            raise ValueError("The current list of active members must be provided")

        member_ids = {member["id"] for member in members if int(member["status"]) == 2}
        user_ids = {str(member["userId"]): member["id"] for member in members if int(member["status"]) == 2}

        active = set()

        for event in events:
            if event["memberId"] is not None and event["memberId"] in member_ids:
                active.add(event["memberId"])
                continue

            if event["actingUserId"] is not None and user_ids.get(event["actingUserId"], None) is not None:
                active.add(user_ids.get(event["actingUserId"]))
                continue

        return active

    def _get_protected_users(self) -> set[str]:
        # we are looking for all members that have access to the Root collection.
        # also members that are in the MDTP Platform Owners group

        # get the Root collection id
        root_collection_id = self.bitwarden_vault.get_collection_id_by_name("Root")
        self.__logger.info(f"Root collection id: {root_collection_id}")

        users = set()
        for user in self.bitwarden_api.get_users():
            if len(user["collections"]) == 0:
                continue

            for user_collection in user["collections"]:
                if user_collection["id"] == root_collection_id:
                    users.add(user["userId"])

        self.__logger.info(f"Root Collection Protected users: {len(users)}")
        # and get all members of the MDTP Platform Owners group
        owners = self.bitwarden_api.get_users_by_group_name("MDTP Platform Owners")
        authorisers = self.bitwarden_api.get_users_by_group_name("AWS Account Authorisers")
        protected = set(users) | set(owners) | set(authorisers)
        self.__logger.info(f"Protected users: {len(protected)}")
        return protected
