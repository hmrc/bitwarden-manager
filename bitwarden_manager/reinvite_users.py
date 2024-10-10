from typing import Dict, Any
from jsonschema import validate
from datetime import datetime, timedelta

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

MAX_REINVITES = 2
# Bitwarden invites expire after 5 days
MAX_INVITE_DURATION_IN_DAYS = 5
EPOCH_DATE = "1970-01-01"


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
            key = {"username": username}
            record = self.dynamodb_client.get_item_from_table(table_name="bitwarden", key=key)
            if record:
                invite_date = self.get_invite_date(record=record)
                reinvites = record.get("reinvites", 0)
                # total invites defaults to 1 due to the initial invite.
                total_invites = record.get("total_invites", 1)
                today = datetime.today()
                if self.can_reinvite_user(invite_date, today, reinvites):
                    self.reinvite_user(
                        id=user.get("id", ""),
                        username=username,
                        key=key,
                        reinvites=reinvites,
                        total_invites=total_invites,
                    )
                elif self.has_invite_expired(invite_date=invite_date, today=today, reinvites=reinvites):
                    self.bitwarden_api.remove_user(username=username)
            else:
                self.__logger.info(f"No record matches {key} in the DB")

    def has_invite_expired(self, invite_date: datetime, today: datetime, reinvites: int) -> bool:
        days = int(MAX_INVITE_DURATION_IN_DAYS * (reinvites + 1))
        date = today - timedelta(days=days)
        return invite_date < date

    def can_reinvite_user(self, invite_date: datetime, today: datetime, reinvites: int) -> bool:
        return (
            self.has_invite_expired(invite_date=invite_date, today=today, reinvites=reinvites)
            and reinvites < MAX_REINVITES
        )

    def get_invite_date(self, record: Dict[str, Any]) -> datetime:
        return datetime.strptime(record.get("invite_date", EPOCH_DATE), "%Y-%m-%d")

    def reinvite_user(self, id: str, username: str, key: Dict[str, str], reinvites: int, total_invites: int) -> None:
        reinvites += 1
        total_invites += 1
        self.bitwarden_api.reinvite_user(id=id, username=username)
        self.dynamodb_client.update_item_in_table(
            table_name="bitwarden", key=key, reinvites=reinvites, total_invites=total_invites
        )
