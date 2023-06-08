import os

from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from jsonschema import validate

export_vault_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "password": {"type": "string", "description": "password to encrypt the export with"},
    },
    "required": ["password"],
}


class ExportVault:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient):
        self.bitwarden_vault_client = bitwarden_vault_client

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=export_vault_event_schema)
        filepath = self.bitwarden_vault_client.export_vault(
            password=event["password"],
        )
        bucket_name = os.environ["BITWARDEN_BACKUP_BUCKET"]
        self.bitwarden_vault_client.write_file_to_s3(bucket_name, filepath)
        self.bitwarden_vault_client.logout()
