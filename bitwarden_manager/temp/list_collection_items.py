from dataclasses import dataclass
from enum import IntEnum
import json
import logging
import os
import subprocess  # nosec B404
from typing import Any, Dict, List, Optional

from jsonschema import validate

from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError

list_collection_items_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "list_collection_items",
        },
        "collection_name": {"type": "string", "description": "Name of Collection"},
    },
    "required": ["event_name", "collection_name"],
}

CLI_TIMEOUT = 60


class BitwardenCollectionNotFoundError(Exception):
    pass


class BitwardenCollectionDuplicateFoundError(Exception):
    pass


@dataclass
class CollectionItem:
    name: str
    item_type: int
    username: Optional[str] = None

    def __str__(self) -> str:
        rep = f"{self.name} | {self.item_type}"
        if self.username:
            rep = f"{self.name} | {self.item_type} | {self.username}"
        return rep


class CollectionItemType(IntEnum):
    LOGIN = 1
    SECURE_NOTE = 2


class ListCollectionItems:
    def __init__(self, bitwarden_vault_client: BitwardenVaultClient) -> None:
        self.bitwarden_vault_client = bitwarden_vault_client
        self.logger = logging.getLogger()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    def get_collection_id(self, collection_name: str) -> str:
        tmp_env = os.environ.copy()
        tmp_env["BW_SESSION"] = self.bitwarden_vault_client.session_token()
        try:
            output = subprocess.check_output(
                [
                    self.bitwarden_vault_client.cli_executable_path,
                    "list",
                    "org-collections",
                    "--organizationid",
                    self.bitwarden_vault_client.organisation_id,
                ],
                encoding="utf-8",
                env=tmp_env,
                shell=False,
                stderr=subprocess.PIPE,
                text=True,
                timeout=CLI_TIMEOUT,
            )  # nosec B603
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise BitwardenVaultClientError(e)

        data: List[Dict[str, Any]] = json.loads(output)
        return str(self.filter_collection(data, collection_name=collection_name)["id"])

    def filter_collection(self, collections: List[Dict[str, Any]], collection_name: str) -> Dict[str, Any]:
        self.logger.info(f"{collections = }")
        matched = [c for c in collections if c["name"] == collection_name]

        if len(matched) == 0:
            raise BitwardenCollectionNotFoundError(f"{collection_name} not found!")

        if len(matched) > 1:
            raise BitwardenCollectionDuplicateFoundError(f"collections with ids {matched} found")

        return matched[0]

    def list_collection_items(self, collection_id: str) -> List[CollectionItem]:
        tmp_env = os.environ.copy()
        tmp_env["BW_SESSION"] = self.bitwarden_vault_client.session_token()
        try:
            output = subprocess.check_output(
                [
                    self.bitwarden_vault_client.cli_executable_path,
                    "list",
                    "items",
                    "--collectionid",
                    collection_id,
                ],
                encoding="utf-8",
                env=tmp_env,
                shell=False,
                stderr=subprocess.PIPE,
                text=True,
                timeout=CLI_TIMEOUT,
            )  # nosec B603

            data: List[Dict[str, Any]] = json.loads(output)
            collection_items: List[CollectionItem] = []
            for item in data:
                if item.get("login", None) and item.get("type") == CollectionItemType.LOGIN:
                    collection_items.append(
                        CollectionItem(
                            name=item["name"], item_type=int(item["type"]), username=item["login"]["username"]
                        )
                    )
                else:
                    collection_items.append(CollectionItem(name=item["name"], item_type=int(item["type"])))
            return collection_items
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Failed to list items due to: {e.stderr!r}")
            raise BitwardenVaultClientError(e)

    def print_collection_items(self, collection_items: List[CollectionItem]) -> None:
        items_str = "\n".join(str(i) for i in collection_items)
        self.logger.info(f"List of collection items\nname | type | username\n{items_str}")

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=list_collection_items_event_schema)
        collection_items = self.list_collection_items(
            collection_id=self.get_collection_id(collection_name=event["collection_name"])
        )
        self.print_collection_items(collection_items=collection_items)
