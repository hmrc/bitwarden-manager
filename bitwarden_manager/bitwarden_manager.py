from typing import Dict, Any

import boto3

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.export_vault import ExportVault
from bitwarden_manager.redacting_formatter import get_bitwarden_logger


class BitwardenManager:
    def __init__(self) -> None:
        self.__logger = get_bitwarden_logger()
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))

    def run(self, event: Dict[str, Any]) -> None:
        event_name = event["event_name"]
        match event_name:
            case "new_user":
                self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                self.__logger.debug("handling event with OnboardUser")
                OnboardUser(bitwarden_api=self._get_bitwarden_public_api()).run(event=event)
            case "export_vault":
                self.__logger.info(
                    f"retrieved bitwarden vault creds with client id {self._get_bitwarden_vault_client_id()}"
                )
                self.__logger.debug("handling event with ExportVault")
                ExportVault(bitwarden_vault_client=self._get_bitwarden_vault_client()).run(event=event)
            case _:
                self.__logger.info(f"ignoring unknown event '{event_name}'")

    def _get_bitwarden_public_api(self) -> BitwardenPublicApi:
        return BitwardenPublicApi(
            logger=self.__logger,
            client_id=self._get_bitwarden_client_id(),
            client_secret=self._get_bitwarden_client_secret(),
        )

    def _get_bitwarden_vault_client(self) -> BitwardenVaultClient:
        return BitwardenVaultClient(
            logger=self.__logger,
            client_id=self._get_bitwarden_vault_client_id(),
            client_secret=self._get_bitwarden_vault_client_secret(),
            password=self._get_bitwarden_vault_password(),
        )

    def _get_bitwarden_client_id(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/api-client-id")

    def _get_bitwarden_client_secret(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/api-client-secret")

    def _get_bitwarden_vault_client_id(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/vault-client-id")

    def _get_bitwarden_vault_client_secret(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/vault-client-secret")

    def _get_bitwarden_vault_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/vault-password")

    def _get_ldap_username(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-username")

    def _get_ldap_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-password")
