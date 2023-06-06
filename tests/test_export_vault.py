from unittest.mock import Mock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.export_vault import ExportVault


def test_export_vault(mock_client: BitwardenVaultClient) -> None:
    event = {"password": "Encryption Pa$$w0rd"}
    bucket_name = "bitwarden-exports-development-7eh4g0"
    filepath = "test.json"

    ExportVault(bitwarden_vault_client=mock_client).run(event)

    mock_client.export_vault.assert_called_with(password="Encryption Pa$$w0rd")

    export_vault = Mock(return_value=filepath)
    mock_client.return_value = Mock(export_vault=export_vault)
    mock_client.return_value.export_vault.return_value = filepath
    mock_client.write_file_to_s3.assert_called_with(bucket_name, filepath)


def test_export_vault_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client = Mock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'password' is a required property"):
        ExportVault(bitwarden_vault_client=mock_client).run(event)

    assert not mock_client.export_vault.called
