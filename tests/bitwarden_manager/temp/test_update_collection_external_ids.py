import logging
import os
import pathlib
from unittest.mock import Mock, patch

import pytest
import responses

from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from bitwarden_manager.temp.update_collection_external_ids import BitwardenCollection, UpdateCollectionExternalIds
from responses import matchers

from tests.bitwarden_manager.clients.test_bitwarden_public_api import MOCKED_LOGIN


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
    s3_client = Mock()
    with open(pathlib.Path(__file__).parent.joinpath("./data_export.json"), "r") as f:
        s3_client.read_object.return_value = f.read()

    expected = [
        BitwardenCollection(name="test-col01", externalId="extId-test-col01"),
        BitwardenCollection(name="test-col02", externalId="extId-test-col02"),
    ]

    got = UpdateCollectionExternalIds(
        bitwarden_api=Mock(), bitwarden_vault_client=Mock(), s3_client=s3_client
    ).get_external_ids_from_data_export()
    assert expected == got


def test_get_org_collections(client: BitwardenVaultClient) -> None:
    expected = [
        BitwardenCollection(id="id-test-collection-01", name="test-collection-01"),
        BitwardenCollection(id="id-test-collection-02", name="test-collection-02"),
        BitwardenCollection(id="id-test-collection", name="test collection"),
    ]

    assert (
        expected
        == UpdateCollectionExternalIds(
            bitwarden_api=Mock(), bitwarden_vault_client=client, s3_client=Mock()
        ).get_org_collections()
    )

    with pytest.raises(BitwardenVaultClientError):
        client.cli_executable_path = str(
            pathlib.Path(__file__).parent.joinpath("./stubs/bitwarden_client_stub_failing.py")
        )
        UpdateCollectionExternalIds(
            bitwarden_api=Mock(), bitwarden_vault_client=client, s3_client=Mock()
        ).get_org_collections()


def test_update_collection_external_id() -> None:
    collection_id = "id-test-collection-01"
    external_id = "extId-test-collection-01"

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/{collection_id}",
            status=200,
            match=[matchers.json_params_matcher({"externalId": external_id, "groups": []})],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        UpdateCollectionExternalIds(
            bitwarden_api=client, bitwarden_vault_client=Mock(), s3_client=Mock()
        ).update_collection_external_id(
            collection_id=collection_id,
            external_id=external_id,
        )

        assert len(rsps.calls) == 1
        assert rsps.calls[-1].request.method == "PUT"
        assert rsps.calls[-1].request.url == f"https://api.bitwarden.com/public/collections/{collection_id}"

        rsps.add(
            status=400,
            content_type="application/json",
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/{collection_id}",
            json={"error": "error"},
        )

        with pytest.raises(Exception):
            UpdateCollectionExternalIds(
                bitwarden_api=client, bitwarden_vault_client=Mock(), s3_client=Mock()
            ).update_collection_external_id(
                collection_id=collection_id,
                external_id=external_id,
            )


def test_reconcile_collection_external_ids() -> None:
    collection_01 = "test-collection-01"
    collection_02 = "test-collection-02"
    from_export_data_collections = [
        BitwardenCollection(
            name=collection_01, id=f"data-export-id-{collection_01}", externalId=f"ext-id-{collection_01}"
        ),
        BitwardenCollection(
            name=collection_02, id=f"data-export-id-{collection_02}", externalId=f"ext-id-{collection_02}"
        ),
    ]

    org_collections = [
        BitwardenCollection(name=collection_01, id=f"id-{collection_01}", externalId=""),
        BitwardenCollection(name=collection_02, id=f"id-{collection_02}", externalId=""),
    ]

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        rsps.add(MOCKED_LOGIN)
        rsps.add(
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/id-{collection_01}",
            status=200,
            match=[matchers.json_params_matcher({"externalId": f"ext-id-{collection_01}", "groups": []})],
        )
        rsps.add(
            method=responses.PUT,
            url=f"https://api.bitwarden.com/public/collections/id-{collection_02}",
            status=200,
            match=[matchers.json_params_matcher({"externalId": f"ext-id-{collection_02}", "groups": []})],
        )

        client = BitwardenPublicApi(
            logger=logging.getLogger(),
            client_id="foo",
            client_secret="bar",
        )

        UpdateCollectionExternalIds(
            bitwarden_api=client, bitwarden_vault_client=Mock(), s3_client=Mock()
        ).reconcile_collection_external_ids(
            from_data_export_collections=from_export_data_collections, org_collections=org_collections
        )

        assert len(rsps.calls) == 3
        assert rsps.calls[-1].request.method == "PUT"


@patch("bitwarden_manager.temp.update_collection_external_ids.UpdateCollectionExternalIds.get_org_collections")
@patch(
    "bitwarden_manager.temp.update_collection_external_ids.UpdateCollectionExternalIds.get_external_ids_from_data_export"  # noqa: E501
)
def test_run(mock_get_external_ids: Mock, mock_get_org_collections: Mock) -> None:
    mock_get_external_ids.return_value = []
    mock_get_org_collections.return_value = []
    event = {"event_name": "update_collection_external_ids"}
    UpdateCollectionExternalIds(bitwarden_api=Mock(), bitwarden_vault_client=Mock(), s3_client=Mock()).run(event)


@patch("bitwarden_manager.bitwarden_manager.UpdateCollectionExternalIds")
@patch("bitwarden_manager.redacting_formatter.RedactingFormatter")
@patch("boto3.client")
def test_update_collection_external_ids_event_routing(
    mock_secretsmanager: Mock, mock_log_redacting_formatter: Mock, mock_update_collection_external_ids: Mock
) -> None:
    event = {"event_name": "update_collection_external_ids"}

    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    mock_update_collection_external_ids.return_value.run.return_value = None
    mock_log_redacting_formatter.validate_patterns.return_value = None
    BitwardenManager().run(event=event)
    mock_update_collection_external_ids.return_value.run.assert_called()
