from unittest.mock import Mock

import pytest
from jsonschema.exceptions import ValidationError

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.export_vault import ExportVault


def test_export_vault() -> None:
    event = {"password": "Encryption Pa$$w0rd"}
    mock_client = Mock(spec=BitwardenVaultClient)

    ExportVault(bitwarden_vault_client=mock_client).run(event)

    mock_client.export_vault.assert_called_with(password="Encryption Pa$$w0rd")


def test_export_vault_rejects_bad_events() -> None:
    event = {"somthing?": 1}
    mock_client = Mock(spec=BitwardenVaultClient)

    with pytest.raises(ValidationError, match="'password' is a required property"):
        ExportVault(bitwarden_vault_client=mock_client).run(event)

    assert not mock_client.export_vault.called
