import json
import os
from typing import Dict, Any

import boto3

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient, BitwardenVaultClientLoginError
from bitwarden_manager.clients.s3_client import S3Client
from bitwarden_manager.clients.dynamodb_client import DynamodbClient
from bitwarden_manager.clients.user_management_api import UserManagementApi
from bitwarden_manager.confirm_user import ConfirmUser
from bitwarden_manager.offboard_user import OffboardUser
from bitwarden_manager.onboard_user import OnboardUser
from bitwarden_manager.export_vault import ExportVault
from bitwarden_manager.reinvite_users import ReinviteUsers
from bitwarden_manager.redacting_formatter import get_bitwarden_logger
from bitwarden_manager.temp.list_collection_items import ListCollectionItems
from bitwarden_manager.temp.list_custom_groups import ListCustomGroups
from bitwarden_manager.temp.update_collection_external_ids import UpdateCollectionExternalIds
from bitwarden_manager.update_user_groups import UpdateUserGroups
from bitwarden_manager.check_user_details import CheckUserDetails


class BitwardenManager:
    def __init__(self) -> None:
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))
        self.__logger = get_bitwarden_logger(
            extra_redaction_patterns=[self._get_bitwarden_export_encryption_password()]
        )

    def is_sqs_event(self, event: Dict[str, Any]) -> bool:
        return "eventSource" in event.get("Records", [{}])[0] and event["Records"][0]["eventSource"] == "aws:sqs"

    def run(self, event: Dict[str, Any]) -> None:
        if self.is_sqs_event(event=event):
            for record in event["Records"]:
                self._run(json.loads(record["body"]))
        else:
            self._run(event=event)

    def _run(self, event: Dict[str, Any]) -> None:

        if (event.get("event_name") is not None) and ("event_name" in event):
            event_name = event["event_name"]
        else:
            event_name = event["path"].replace("/", " ").replace("?", " ").replace("-", "_").split()[-1]

        self.__logger.debug("%s", event)
        bitwarden_vault_client = self._get_bitwarden_vault_client()
        try:
            match event_name:
                case "new_user":
                    self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                    self.__logger.debug("handling event with OnboardUser")
                    OnboardUser(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)
                case "update_user_groups":
                    self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                    self.__logger.debug("handling event with UpdateUserGroups")
                    UpdateUserGroups(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                    ).run(event=event)
                case "export_vault":
                    self.__logger.debug("handling event with ExportVault")
                    ExportVault(bitwarden_vault_client=bitwarden_vault_client, s3_client=S3Client()).run(event=event)
                case "confirm_user":
                    self.__logger.debug("handling event with ConfirmUser")
                    ConfirmUser(
                        bitwarden_vault_client=bitwarden_vault_client, allowed_domains=self._get_allowed_email_domains()
                    ).run(event=event)
                case "check_user":
                    self.__logger.debug("handling event with CheckUserDetails")
                    CheckUserDetails(
                        bitwarden_api=self._get_bitwarden_public_api(), bitwarden_vault_client=bitwarden_vault_client
                    ).run(event=event)
                case "remove_user":
                    self.__logger.debug("handling event with OffboardUser")
                    OffboardUser(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)
                case "reinvite_users":
                    self.__logger.info("handling reinvite users event with ReinviteUsers")
                    ReinviteUsers(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)
                case "list_custom_groups":
                    self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                    self.__logger.debug("handling event with ListCustomGroups")
                    ListCustomGroups(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                    ).run(event=event)
                case "list_collection_items":
                    self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                    ListCollectionItems(
                        bitwarden_vault_client=bitwarden_vault_client,
                    ).run(event=event)
                case "update_collection_external_ids":
                    self.__logger.info(f"retrieved ldap creds with username {self._get_ldap_username()}")
                    UpdateCollectionExternalIds(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                        s3_client=S3Client(),
                    ).run(event=event)
                case _:
                    self.__logger.info(f"ignoring unknown event '{event_name}'")
        except BitwardenVaultClientLoginError as e:
            self.__logger.warning(f"Failed to complete {event_name} due to Bitwarden CLI login error - {e}")
        finally:
            bitwarden_vault_client.logout()

    def _get_bitwarden_cli_timeout(self) -> float:
        timeout = os.environ.get("BITWARDEN_CLI_TIMEOUT", "20")
        if timeout.isnumeric():
            return float(timeout)
        return 20.0

    def _get_allowed_email_domains(self) -> list[str]:
        domain_list = os.environ.get("ALLOWED_DOMAINS", "").split(",")
        if domain_list == [""]:
            return []
        else:
            return list(map(lambda txt: txt.strip(), domain_list))

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
            cli_executable_path="bw",
            organisation_id=self._get_organisation_id(),
            cli_timeout=self._get_bitwarden_cli_timeout(),
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
