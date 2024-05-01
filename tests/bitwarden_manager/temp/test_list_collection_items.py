import logging
import pathlib
from typing import List
from unittest.mock import Mock, patch

from pytest import LogCaptureFixture, mark
import pytest
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


def test_filter_collection(client: BitwardenVaultClient) -> None:
    collections = [
        {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
        {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
    ]
    id = ListCollectionItems(bitwarden_vault_client=client).filter_collection(
        collections=collections, collection_name="test-collection-01"
    )["id"]
    assert "id-test-collection-01" == id

    collections = [
        {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
        {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
        {"object": "collection", "id": "id-another-test-collection-01", "name": "test-collection-01"},
    ]
    with pytest.raises(BitwardenCollectionDuplicateFoundError):
        ListCollectionItems(bitwarden_vault_client=client).filter_collection(
            collections=collections, collection_name="test-collection-01"
        )

    collections = [
        {"object": "collection", "id": "id-test-collection-01", "name": "test-collection-01"},
        {"object": "collection", "id": "id-test-collection-02", "name": "test-collection-02"},
    ]
    with pytest.raises(BitwardenCollectionNotFoundError):
        ListCollectionItems(bitwarden_vault_client=client).filter_collection(
            collections=collections, collection_name="test-collection-X"
        )


@mark.parametrize(
    "collection_name,expected",
    [
        ("test-collection-01", "id-test-collection-01"),
        ("test-collection-02", "id-test-collection-02"),
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
