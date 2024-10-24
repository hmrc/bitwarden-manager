import os
import tempfile

from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.s3_client import S3Client
from datetime import datetime

from bitwarden_manager.redacting_formatter import get_bitwarden_logger


class ExportVault:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient, s3_client: S3Client):
        self.bitwarden_vault_client = bitwarden_vault_client
        self.s3_client = s3_client
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def run(self, event: Dict[str, Any]) -> None:
        self.__logger.info("Creating vault backup.")

        backup_name = f"bw_backup_{datetime.now().isoformat()}.json"
        bucket_name = os.environ["BITWARDEN_BACKUP_BUCKET"]
        with tempfile.NamedTemporaryFile() as backup_file:
            self.bitwarden_vault_client.export_vault(file_path=backup_file.name)
            self.s3_client.write_file_to_s3(bucket_name=bucket_name, filepath=backup_file.name, filename=backup_name)
