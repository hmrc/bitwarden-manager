from typing import Dict, Any

import boto3

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient
from bitwarden_manager.clients.s3_client import S3Client
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.export_vault import ExportVault
from bitwarden_manager.redacting_formatter import get_bitwarden_logger


class BitwardenManager:
    def __init__(self) -> None:
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))
        self.__logger = get_bitwarden_logger(
            extra_redaction_patterns=[self._get_bitwarden_export_encryption_password()]
        )

    def run(self, event: Dict[str, Any]) -> None:
        event_name = event["event_name"]
        bitwarden_vault_client = self._get_bitwarden_vault_client()
        match event_name:
            case "new_user":
                self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                self.__logger.debug("handling event with OnboardUser")
                OnboardUser(
                    bitwarden_api=self._get_bitwarden_public_api(),
                    user_management_api=self._get_user_management_api(),
                    bitwarden_vault_client=bitwarden_vault_client,
                ).run(event=event)
            case "export_vault":
                self.__logger.debug("handling event with ExportVault")
                ExportVault(bitwarden_vault_client=bitwarden_vault_client, s3_client=S3Client()).run(event=event)
            case _:
                self.__logger.info(f"ignoring unknown event '{event_name}'")
        bitwarden_vault_client.logout()

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
            export_enc_password=self._get_bitwarden_export_encryption_password(),
            cli_executable_path="./bw",
            organisation_id=self._get_organisation_id(),
        )

    def _get_user_management_api(self) -> UserManagementApi:
        return UserManagementApi(
            logger=self.__logger,
            client_id=self._get_ldap_username(),
            client_secret=self._get_ldap_password(),
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

    def _get_bitwarden_export_encryption_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/export-encryption-password")

    def _get_ldap_username(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-username")

    def _get_ldap_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-password")

    def _get_organisation_id(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/organisation-id")
