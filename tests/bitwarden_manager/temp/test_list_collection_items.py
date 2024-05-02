import logging
import pathlib
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from pytest import LogCaptureFixture, mark
import pytest
from bitwarden_manager.bitwarden_manager import BitwardenManager
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from bitwarden_manager.temp.list_collection_items import (
    BitwardenCollectionDuplicateFoundError,
    BitwardenCollectionNotFoundError,
    CollectionItem,
    CollectionItemType,
    ListCollectionItems,
)


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


@mark.parametrize(
    "input,expected",
    [
        (
            [
                CollectionItem(name="login01", item_type=CollectionItemType.LOGIN, username="some@user.com"),
                CollectionItem(name="note01", item_type=CollectionItemType.SECURE_NOTE),
            ],
            "login01 | 1 | some@user.com\nnote01 | 2",
        ),
        (
            [
                CollectionItem(name="login02", item_type=CollectionItemType.LOGIN, username="another@user.com"),
                CollectionItem(name="note02", item_type=CollectionItemType.SECURE_NOTE),
            ],
            "login02 | 1 | another@user.com\nnote02 | 2",
        ),
    ],
)
def test_print_collection_items(input: List[CollectionItem], expected: str, caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        ListCollectionItems(bitwarden_vault_client=Mock()).print_collection_items(collection_items=input)
    assert expected in caplog.text


def test_list_collection_items(client: BitwardenVaultClient) -> None:
    expected = [
        CollectionItem(name="login01", item_type=CollectionItemType.LOGIN, username="some@user.com"),
        CollectionItem(name="login02", item_type=CollectionItemType.LOGIN, username="another@user.com"),
        CollectionItem(name="login03", item_type=CollectionItemType.LOGIN, username="awesome@user.com"),
        CollectionItem(name="note01", item_type=CollectionItemType.SECURE_NOTE),
        CollectionItem(name="note02", item_type=CollectionItemType.SECURE_NOTE),
    ]

    collection_items = ListCollectionItems(bitwarden_vault_client=client).list_collection_items(
        collection_id="collection_id"
    )

    assert collection_items == expected

    with pytest.raises(BitwardenVaultClientError):
        client.cli_executable_path = str(
            pathlib.Path(__file__).parent.joinpath("./stubs/bitwarden_client_stub_failing.py")
        )
        ListCollectionItems(bitwarden_vault_client=client).list_collection_items(collection_id="collection_id")


@mark.parametrize(
    "collection_name,collections,expected",
    [
        (
            "test-collection-01",
            [
                {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
                {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
            ],
            "id-test-collection-01",
        ),
        (
            "Platform Security",
            [
                {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
                {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
                {"object": "collection", "id": "id-platform-security", "name": "Platform Security"},
            ],
            "id-platform-security",
        ),
    ],
)
def test_filter_collection(
    collection_name: str, collections: List[Dict[str, Any]], expected: str, client: BitwardenVaultClient
) -> None:
    id = ListCollectionItems(bitwarden_vault_client=client).filter_collection(
        collections=collections, collection_name=collection_name
    )["id"]
    assert expected == id


@mark.parametrize(
    "collection_name,collections,error",
    [
        (
            "test-collection-01",
            [
                {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
                {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
                {"object": "collection", "id": "id-another-test-collection-01", "name": "test-collection-01"},
            ],
            BitwardenCollectionDuplicateFoundError,
        ),
        (
            "missing-collection",
            [
                {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
                {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
            ],
            BitwardenCollectionNotFoundError,
        ),
    ],
)
def test_filter_collection_fails(
    collection_name: str, collections: List[Dict[str, Any]], error: Any, client: BitwardenVaultClient
) -> None:
    with pytest.raises(error):
        ListCollectionItems(bitwarden_vault_client=client).filter_collection(
            collections=collections, collection_name=collection_name
        )


@mark.parametrize(
    "collection_name,expected",
    [
        ("test-collection-01", "id-test-collection-01"),
        ("test-collection-02", "id-test-collection-02"),
        ("test collection", "id-test-collection"),
    ],
)
def test_get_collection_id(collection_name: str, expected: str, client: BitwardenVaultClient) -> None:
    assert expected == ListCollectionItems(bitwarden_vault_client=client).get_collection_id(
        collection_name=collection_name
    )

    with pytest.raises(BitwardenVaultClientError):
        client.cli_executable_path = str(
            pathlib.Path(__file__).parent.joinpath("./stubs/bitwarden_client_stub_failing.py")
        )
        ListCollectionItems(bitwarden_vault_client=client).get_collection_id(collection_name=collection_name)


@patch("bitwarden_manager.temp.list_collection_items.ListCollectionItems.print_collection_items")
@patch("bitwarden_manager.temp.list_collection_items.ListCollectionItems.list_collection_items")
@patch("bitwarden_manager.temp.list_collection_items.ListCollectionItems.get_collection_id")
def test_run(mock_get: Mock, mock_list: Mock, mock_print: Mock) -> None:
    mock_list.return_value = []
    event = {"event_name": "list_collection_items", "collection_name": "test-collection"}
    ListCollectionItems(bitwarden_vault_client=Mock()).run(event)


@patch("bitwarden_manager.bitwarden_manager.ListCollectionItems")
@patch("bitwarden_manager.redacting_formatter.RedactingFormatter")
@patch("boto3.client")
def test_list_custom_groups_event_routing(
    mock_secretsmanager: Mock, mock_log_redacting_formatter: Mock, mock_list_custom_groups: Mock
) -> None:
    event = {"event_name": "list_collection_items", "collection_name": "test-collection"}

    get_secret_value = Mock(return_value={"SecretString": "secret"})
    mock_secretsmanager.return_value = Mock(get_secret_value=get_secret_value)
    mock_list_custom_groups.return_value.run.return_value = None
    mock_log_redacting_formatter.validate_patterns.return_value = None
    BitwardenManager().run(event=event)
    mock_list_custom_groups.return_value.run.assert_called()
