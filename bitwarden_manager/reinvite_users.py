from typing import Dict, Any
from jsonschema import validate
from datetime import datetime

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.redacting_formatter import get_bitwarden_logger


reinvite_users_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {"type": "string", "description": "name of the current event", "pattern": "reinvite_users"},
    },
    "required": ["event_name"],
}

MAX_INVITES_PER_RUN = 2  # three invites per run, zero based
MAX_INVITES_TOTAL = 9  # max three runs before we ignore them, one based

INVITE_VALID_DURATION_IN_DAYS = 5
EPOCH_DATE = "1970-01-01"
DYNAMODB_TABLE_NAME = "bitwarden"


class ReinviteUsers:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        dynamodb_client: DynamodbClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.dynamodb_client = dynamodb_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=reinvite_users_event_schema)

        for user in self.bitwarden_api.get_pending_users():
            username = user.get("externalId", "")
            table_key = {"username": username}
            record = self.dynamodb_client.get_item_from_table(table_name=DYNAMODB_TABLE_NAME, key=table_key)

            if record:
                if self.can_invite_user(
                    self.str_to_datetime(record.get("invite_date", EPOCH_DATE)),
                    record.get("reinvites", 0),
                    record.get("total_invites", 1),
                ):
                    self.__logger.info(f"Inviting user, {username}...")
                    self.invite_user(user.get("id", ""), username, table_key, record)
                else:
                    self.__logger.info(f"User {username} not eligible for invite, removing...")
                    self.bitwarden_api.remove_user(username=username)
            else:
                self.__logger.info(f"User {username} does not exist in dynamodb table {DYNAMODB_TABLE_NAME}, removing")
                self.bitwarden_api.remove_user(username=username)

    def can_invite_user(self, invite_date: datetime, invites_this_run: int, total_invites: int) -> bool:
        return (
            self.has_invite_expired(invite_date=invite_date)
            and not self.has_reached_max_invites_per_run(invites=invites_this_run)
            and not self.has_reached_max_total_invites(invites=total_invites)
        )

    def has_invite_expired(self, invite_date: datetime) -> bool:
        return (datetime.today() - invite_date).days > INVITE_VALID_DURATION_IN_DAYS

    def has_reached_max_invites_per_run(self, invites: int) -> bool:
        return invites >= MAX_INVITES_PER_RUN

    def has_reached_max_total_invites(self, invites: int):
        return invites >= MAX_INVITES_TOTAL

    def str_to_datetime(self, date: str) -> datetime:
        return datetime.strptime(date, "%Y-%m-%d")

    def datetime_to_str(self, date: datetime) -> str:
        return date.strftime("%Y-%m-%d")

    def invite_user(
        self, bitwarden_id: str, username: str, dynamodb_table_key: Dict[str, str], dynamodb_record: Dict[str, Any]
    ) -> None:
        self.bitwarden_api.reinvite_user(id=bitwarden_id, username=username)

        self.dynamodb_client.update_item_in_table(
            table_name=DYNAMODB_TABLE_NAME,
            key=dynamodb_table_key,
            item={
                "invite_date": self.datetime_to_str(datetime.today()),
                "reinvites": dynamodb_record.get("invites", 0) + 1,
                "total_invites": dynamodb_record.get("total_invites", 1) + 1,
            },
        )
