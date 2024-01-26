from typing import Dict, Any
from jsonschema import validate

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.dynamodb_client import DynamodbClient


reinvite_users_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {"type": "string", "description": "name of the current event", "pattern": "reinvite_users"},
    },
    "required": ["event_name"],
}


class ReinviteUsers:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        dynamodb_client: DynamodbClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.dynamodb_client = dynamodb_client

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=reinvite_users_event_schema)
        self.bitwarden_api.get_pending_users()
