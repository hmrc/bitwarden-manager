import os

from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


class ExportVault:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient):
        self.bitwarden_vault_client = bitwarden_vault_client

    def run(self, event: Dict[str, Any]) -> None:
        org_id = os.environ["ORGANISATION_ID"]
        bucket_name = os.environ["BITWARDEN_BACKUP_BUCKET"]
        filepath = self.bitwarden_vault_client.export_vault(org_id=org_id)
        self.bitwarden_vault_client.write_file_to_s3(bucket_name, filepath)
        self.bitwarden_vault_client.logout()
