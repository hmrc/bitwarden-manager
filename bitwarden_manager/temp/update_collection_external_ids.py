# read a data export json file
#  - variable / input
# fetch the org-collections (cli)
# reconcile collection externalid using information from data export json file (api)


from dataclasses import dataclass
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from requests import HTTPError 
from bitwarden_manager.clients.bitwarden_public_api import API_URL, REQUEST_TIMEOUT_SECONDS, BitwardenPublicApi, session
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientError

CLI_TIMEOUT = 60


@dataclass
class BitwardenCollection:
    name: str
    id: Optional[str] = None
    externalId: Optional[str] = None


class UpdateCollectionExternalIds:

    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        bitwarden_vault_client: BitwardenVaultClient
    ) -> None:
        self.bitwarden_api = bitwarden_api
        self.bitwarden_vault_client = bitwarden_vault_client
        self.logger = logging.getLogger()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )

    def read_external_ids_from_data_export(self, data_export_file: str) -> List[BitwardenCollection]:
        with open(data_export_file, 'r') as f:
            data = json.load(f)
        return [BitwardenCollection(name=c["name"], externalId=c["externalId"]) for c in data["collections"]]

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
        put_response = session.put(
            f"{API_URL}/collections/{collection_id}",
            json={
                "externalId": external_id,
                "groups": [],  # not a problem when run just after import
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            put_response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to update the collection externalId") from error

    def reconcile_collection_external_ids(self, from_data_export_collections: List[BitwardenCollection], org_collections: List[BitwardenCollection]) -> None:
        for c in from_data_export_collections:
            for org_c in org_collections:
                if c.name == org_c.name:
                    self.update_collection_external_id(collection_id=org_c.id, external_id=c.externalId)

    def run(self) -> None:
        from_data_export_collections = self.read_external_ids_from_data_export()

        org_collections = self.get_org_collections()

        self.reconcile_collection_external_ids(from_data_export_collections=from_data_export_collections, org_collections=org_collections)
