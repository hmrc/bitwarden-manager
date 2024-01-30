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

MAX_REINVITES = 1


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
        # Bitwarden invites expire after 5 days
        date = datetime.today() - timedelta(days=5)
        for user in self.bitwarden_api.get_pending_users():
            username = user.get("externalId", "")
            key = {"username": username}
            self.__logger.debug(f"Key = {key}")
            record = self.dynamodb_client.get_item_from_table(table_name="bitwarden", key=key)
            self.__logger.debug(f"Record = {record}")
            invite_date = datetime.strptime(record.get("invite_date", ""), "%Y-%m-%d")
            reinvites = record.get("reinvites", 0)
            if invite_date < date and reinvites < MAX_REINVITES:
                self.bitwarden_api.reinvite_user(id=user.get("id", ""), username=username)
                reinvites += 1
                self.dynamodb_client.update_item_in_table(table_name="bitwarden", key=key, reinvites=reinvites)
