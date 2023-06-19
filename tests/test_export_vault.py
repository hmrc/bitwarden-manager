import mock
import os

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.export_vault import ExportVault
from unittest.mock import Mock, MagicMock


@mock.patch.dict(os.environ, {"BITWARDEN_BACKUP_BUCKET": "test-bucket"})
def test_export_vault() -> None:
    event = {"event_name": "export_vault"}
    filepath = "test.json"
    mock_client = Mock(spec=BitwardenVaultClient)
    mock_client.export_vault = MagicMock(return_value=filepath)

    ExportVault(bitwarden_vault_client=mock_client).run(event)

    mock_client.write_file_to_s3.assert_called_with("test-bucket", filepath)
    assert mock_client.logout.called
