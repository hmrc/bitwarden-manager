from dataclasses import dataclass
import json
import logging
import os
import subprocess  # nosec B404
from typing import Any, Dict, List

from jsonschema import validate
from requests import HTTPError
from bitwarden_manager.clients.bitwarden_public_api import API_URL, REQUEST_TIMEOUT_SECONDS, BitwardenPublicApi, session
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError
from bitwarden_manager.clients.s3_client import S3Client

CLI_TIMEOUT = 60
BITWARDEN_DATA_EXPORT_FILENAME = "bitwarden-data-export-US-org.json"

update_collection_external_ids_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
            "pattern": "update_collection_external_ids",
        },
    },
    "required": ["event_name"],
}

data_export_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "encrypted": {"type": "boolean", "description": "Whether data export is encrypted"},
        "collections": {
            "description": "List of collection objects",
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "organizationId": {"type": "string"},
                    "name": {"type": "string"},
                    "externalId": {"type": ["string", None]},
                },
            },
        },
    },
    "required": ["encrypted", "collections"],
}


@dataclass
class BitwardenCollection:
    name: str
    id: str = ""
    externalId: str = ""


class UpdateCollectionExternalIds:

    def __init__(
        self, bitwarden_api: BitwardenPublicApi, bitwarden_vault_client: BitwardenVaultClient, s3_client: S3Client
    ) -> None:
        self.bitwarden_api = bitwarden_api
        self.bitwarden_vault_client = bitwarden_vault_client
        self.s3_client = s3_client
        self.logger = logging.getLogger()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    def get_external_ids_from_data_export(self) -> List[BitwardenCollection]:
        bucket_name = os.environ["BITWARDEN_BACKUP_BUCKET"]

        json_data = json.loads(self.s3_client.read_object(bucket_name=bucket_name, key=BITWARDEN_DATA_EXPORT_FILENAME))
        validate(instance=json_data, schema=data_export_schema)

        return [BitwardenCollection(name=c["name"], externalId=c["externalId"]) for c in json_data["collections"]]

    def get_org_collections(self) -> List[BitwardenCollection]:
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
        return [BitwardenCollection(name=c["name"], id=c["id"]) for c in data]

    def update_collection_external_id(self, collection_id: str, external_id: str) -> None:
        response = session.put(
            f"{API_URL}/collections/{collection_id}",
            json={
                "externalId": external_id,
                "groups": [],  # not a problem when run just after import
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to update the collection externalId") from error

    def reconcile_collection_external_ids(
        self, from_data_export_collections: List[BitwardenCollection], org_collections: List[BitwardenCollection]
    ) -> None:
        self.bitwarden_api._BitwardenPublicApi__fetch_token()  # type: ignore
        for c in from_data_export_collections:
            for org_c in org_collections:
                if c.name == org_c.name:
                    self.update_collection_external_id(collection_id=org_c.id, external_id=c.externalId)

    def run(self, event: Dict[str, Any]) -> None:
        validate(instance=event, schema=update_collection_external_ids_event_schema)
        from_data_export_collections = self.get_external_ids_from_data_export()

        org_collections = self.get_org_collections()

        self.reconcile_collection_external_ids(
            from_data_export_collections=from_data_export_collections, org_collections=org_collections
        )
