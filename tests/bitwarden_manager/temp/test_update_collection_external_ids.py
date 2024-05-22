import logging
import os
import pathlib
from unittest.mock import Mock, patch

import pytest
import responses

from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.temp.update_collection_external_ids import BitwardenCollection, UpdateCollectionExternalIds

@pytest.fixture
def client() -> BitwardenVaultClient:
    return BitwardenVaultClient(
        cli_executable_path=str(pathlib.Path(__file__).parent.joinpath("./stubs/bitwarden_client_stub.py")),
        client_id="test_id",
        client_secret="test_secret",
        export_enc_password="hmrc2023",
        logger=logging.getLogger(),
        organisation_id="abc-123",
        password="very secure pa$$w0rd!",
        cli_timeout=20,
    )

@patch.dict(os.environ, {"BITWARDEN_BACKUP_BUCKET": "bitwarden-backup-bucket"})
def test_get_external_ids_from_data_export() -> None:
    s3client = Mock()
    with open(pathlib.Path(__file__).parent.joinpath("./data_export.json"), 'r') as f:
        s3client.read_object.return_value = f.read()

    expected = [
        BitwardenCollection(name="test-col01", externalId="extId-test-col01"),
        BitwardenCollection(name="test-col02", externalId="extId-test-col02")
    ]

    got = UpdateCollectionExternalIds(bitwarden_api=Mock(), bitwarden_vault_client=client, s3client=s3client).get_external_ids_from_data_export()
    assert expected == got

def test_read_external_ids_from_json_file() -> None:
    expected = [
        BitwardenCollection(name="test-col01", externalId="extId-test-col01"),
        BitwardenCollection(name="test-col02", externalId="extId-test-col02")
    ]

    data_export_file = str(pathlib.Path(__file__).parent.joinpath("./data_export.json"))

    assert expected == UpdateCollectionExternalIds(Mock(), Mock(), Mock()).read_external_ids_from_data_export(data_export_file)


def test_get_org_collections(client: BitwardenVaultClient) -> None:
    expected = [
        BitwardenCollection(id="id-test-collection-01", name="test-collection-01"),
        BitwardenCollection(id="id-test-collection-02", name="test-collection-02"),
        BitwardenCollection(id="id-test-collection", name="test collection"),
    ]

    assert expected == UpdateCollectionExternalIds(bitwarden_api=Mock(), bitwarden_vault_client=client, s3client=Mock()).get_org_collections()

def test_update_collection_external_id() -> None:
    collection_id = "id-test-collection-01"
    external_id = "extId-test-collection-01"

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/collections/{collection_id}",
            status=200,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        UpdateCollectionExternalIds(bitwarden_api=client, bitwarden_vault_client=Mock(), s3client=Mock()).update_collection_external_id(
            collection_id=collection_id,
            external_id=external_id,
        )

        assert len(rsps.calls) == 1
        assert rsps.calls[-1].request.method == "PUT"
        assert rsps.calls[-1].request.url == f"https://api.bitwarden.eu/public/collections/{collection_id}"


def test_reconcile_collection_external_ids() -> None:
    from_export_data_collections = [ 
        BitwardenCollection(name="test-collection-01", id="data-export-id-test-collection-01", externalId="ext-id-test-collection-01"),
        BitwardenCollection(name="test-collection-02", id="data-export-id-test-collection-02", externalId="ext-id-test-collection-02"),
    ]

    org_collections = [ 
        BitwardenCollection( name="test-collection-01", id="id-test-collection-01", externalId=None),
        BitwardenCollection( name="test-collection-02", id="id-test-collection-02", externalId=None),
    ]

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/collections/id-test-collection-01",
            status=200,
        )
        rsps.add(
            responses.PUT,
            f"https://api.bitwarden.eu/public/collections/id-test-collection-02",
            status=200,
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        UpdateCollectionExternalIds(bitwarden_api=client, bitwarden_vault_client=Mock(), s3client=Mock()).reconcile_collection_external_ids(
            from_data_export_collections=from_export_data_collections,
            org_collections=org_collections
        )

        assert len(rsps.calls) == 2
        assert rsps.calls[-1].request.method == "PUT"