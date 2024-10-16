from typing import Dict, Any

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient

from jsonschema import validate

from bitwarden_manager.redacting_formatter import get_bitwarden_logger

offboard_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "remove_user",
        },
        "username": {"type": "string", "description": "the users ldap username"},
    },
    "required": ["event_name", "username"],
}


class OffboardUser:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        dynamodb_client: DynamodbClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.dynamodb_client = dynamodb_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=offboard_user_event_schema)

        self.__logger.info(f"Offboarding user {event['username']}")

        self.__logger.info(f"Removing user {event['username']} from bitwarden")
        self.bitwarden_api.remove_user(
            username=event["username"],
        )

        self.__logger.info(f"Removing user {event['username']} from dynamodb")
        dynamo_key = {"username": event["username"]}
        self.dynamodb_client.delete_item_from_table(table_name="bitwarden", key=dynamo_key)
