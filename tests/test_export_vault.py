import mock
import os
import pytest

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.export_vault import ExportVault
from jsonschema.exceptions import ValidationError
from unittest.mock import Mock, MagicMock


@mock.patch.dict(os.environ, {"BITWARDEN_BACKUP_BUCKET": "test-bucket", "ORGANISATION_ID": "abc-123"})
def test_export_vault() -> None:
    event = {"password": "Encryption Pa$$w0rd"}
    filepath = "test.json"
    mock_client = Mock(spec=BitwardenVaultClient)
    mock_client.export_vault = MagicMock(return_value=filepath)

    ExportVault(bitwarden_vault_client=mock_client).run(event)

    mock_client.export_vault.assert_called_with(org_id="abc-123", password="Encryption Pa$$w0rd")
    mock_client.write_file_to_s3.assert_called_with("test-bucket", filepath)
    assert mock_client.logout.called


def test_export_vault_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client = Mock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'password' is a required property"):
        ExportVault(bitwarden_vault_client=mock_client).run(event)

    assert not mock_client.export_vault.called
