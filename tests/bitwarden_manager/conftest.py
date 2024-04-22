import logging
import os
import pathlib
from unittest import mock
import pytest

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient


@pytest.fixture
def client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./clients/stubs/bitwarden_client_stub.py")),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=20,
    )


@pytest.fixture
@mock.patch.dict(os.environ, {"BITWARDEN_CLI_TIMEOUT": "1"})
def timeout_client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./clients/stubs/bitwarden_client_stub.py")),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=float(os.environ.get("BITWARDEN_CLI_TIMEOUT", "20")),
    )


@pytest.fixture
def failing_client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(
            pathlib.Path(__file__).parent.joinpath("./clients/stubs/bitwarden_client_failing_operations_stub.py")
        ),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=20,
    )


@pytest.fixture
def failing_authentication_client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(
            pathlib.Path(__file__).parent.joinpath("./clients/stubs/bitwarden_client_failing_authentication_stub.py")
        ),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=20,
    )
