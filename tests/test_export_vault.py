import mock
import os

from freezegun import freeze_time

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.s3_client import S3Client
from bitwarden_manager.export_vault import ExportVault
from unittest.mock import Mock


@mock.patch.dict(os.environ, {"BITWARDEN_BACKUP_BUCKET": "test-bucket"})
@freeze_time("2023-7-17")
def test_export_vault() -> None:
    event = {"event_name": "export_vault"}
    s3_client = Mock(spec=S3Client)
    bitwarden_client = Mock(spec=BitwardenVaultClient)

    ExportVault(bitwarden_vault_client=bitwarden_client, s3_client=s3_client).run(event)

    bitwarden_client.export_vault.assert_called_once()
    expected_file_path = bitwarden_client.export_vault.mock_calls[0].kwargs["file_path"]
    assert "tmp" in expected_file_path
    s3_client.write_file_to_s3.assert_called_with(
        bucket_name="test-bucket", filepath=expected_file_path, filename="bw_backup_2023-07-17T00:00:00.json"
    )
