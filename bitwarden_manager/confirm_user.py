from typing import Dict, Any, List
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from jsonschema import validate

from bitwarden_manager.redacting_formatter import get_bitwarden_logger

confirm_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {"type": "string", "description": "name of the current event", "pattern": "confirm_user"},
    },
    "required": ["event_name"],
}


class BitwardenConfirmUserInvalidDomain(Exception):
    pass


class ConfirmUser:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient, allowed_domains: list[str]):
        self.bitwarden_vault_client = bitwarden_vault_client
        self.allowed_domains = allowed_domains
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=confirm_user_event_schema)

        self.__logger.info("Processing user confirmations")
        unconfirmed_users = self.bitwarden_vault_client.list_unconfirmed_users()
        self.confirm_valid_users(unconfirmed_users, self.allowed_domains)

    def confirm_valid_users(self, unconfirmed_users: list[Dict[str, str]], allowed_domains: list[str]) -> None:
        errors: List[Exception] = []
        for user in unconfirmed_users:
            self.__logger.info(f"Processing confirmations for {user['email']}")
            user_email = user["email"]
            user_id = user["id"]
            domain = user_email.split("@")[-1]

            if domain in allowed_domains:
                try:
                    self.bitwarden_vault_client.confirm_user(user_id=user_id)
                    self.__logger.info(f"User {user['email']} confirmed.")
                except BitwardenVaultClientError as e:
                    errors.append(e)
            else:
                self.__logger.info(f"Error confirming user {user['email']}. The domain {domain} is not permitted.")
                errors.append(BitwardenConfirmUserInvalidDomain(f"Invalid Domain detected: {domain}"))

        if errors:
            raise ExceptionGroup("User Confirmation Errors: ", errors)
