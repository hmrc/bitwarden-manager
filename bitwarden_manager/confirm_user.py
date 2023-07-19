from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from jsonschema import validate

confirm_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {"type": "string", "description": "name of the current event", "pattern": "confirm_user"},
        "allowed_domains": {"type": "array", "description": "approved domains that can be automatically confirmed"},
    },
    "required": ["event_name", "allowed_domains"],
}


class ConfirmUser:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient):
        self.bitwarden_vault_client = bitwarden_vault_client

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=confirm_user_event_schema)
        unconfirmed_users = self.bitwarden_vault_client.list_unconfirmed_users()
        self.confirm_valid_users(unconfirmed_users, event["allowed_domains"])

    def confirm_valid_users(self, unconfirmed_users: list[Dict[str, str]], allowed_domains: list[str]) -> None:
        errors = []
        for user in unconfirmed_users:
            user_email = user["email"]
            user_id = user["id"]

            if user_email.split("@")[-1] in allowed_domains:
                try:
                    self.bitwarden_vault_client.confirm_user(user_id)
                except BitwardenVaultClientError as e:
                    errors.append(e)
        if errors:
            raise BitwardenVaultClientError(f"Confirmation process failed on {len(errors)} users")
