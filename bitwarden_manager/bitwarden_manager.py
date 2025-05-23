import json
import os

from typing import Dict, Any

import boto3
from jsonschema import validate

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, BitwardenUserAlreadyExistsException
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
from bitwarden_manager.get_user_details import GetUserDetails


# Only one of ["event_name", "path"] may be present in the event object
event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "event_name": {
            "type": "string",
            "description": "name of the current event",
        },
        "path": {"type": "string", "description": "API request path"},
    },
    "oneOf": [
        {"required": ["event_name"]},
        {"required": ["path"]},
    ],
}


class BitwardenManager:
    def __init__(self) -> None:
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))

        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[self._get_secret("export-encryption-password")])

    def _is_api_gateway_event(self, event: Dict[str, Any]) -> Any:
        return event.get("path") and "/bitwarden-manager/" in event["path"]

    def run(self, event: Dict[str, Any]) -> Dict[str, Any] | None:
        if self._is_api_gateway_event(event=event):
            return self._api_run(event=event)
        elif self._is_sqs_event(event=event):
            for record in event["Records"]:
                self._run(json.loads(record["body"]))
        else:
            self._run(event=event)
        return None

    def _run(self, event: Dict[str, Any]) -> None:
        self.__logger.debug("%s", event)
        validate(instance=event, schema=event_schema)

        event_name = event.get("event_name")
        bitwarden_vault_client = self._get_bitwarden_vault_client()

        try:
            match event_name:
                case "new_user":
                    self.__logger.info(f"Handling event {event_name} with OnboardUser")
                    OnboardUser(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)

                case "update_user_groups":
                    self.__logger.info(f"Handling event {event_name} with UpdateUserGroups")
                    UpdateUserGroups(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                    ).run(event=event)

                case "export_vault":
                    self.__logger.info(f"Handling event {event_name} with ExportVault")
                    ExportVault(bitwarden_vault_client=bitwarden_vault_client, s3_client=S3Client()).run(event=event)

                case "confirm_user":
                    self.__logger.info(f"Handling event {event_name} with ConfirmUser")
                    ConfirmUser(
                        bitwarden_vault_client=bitwarden_vault_client, allowed_domains=self._get_allowed_email_domains()
                    ).run(event=event)

                case "remove_user":
                    self.__logger.info(f"Handling event {event_name} with OffboardUser")
                    OffboardUser(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)

                case "reinvite_users":
                    self.__logger.info(f"Handling event {event_name} with ReinviteUsers")
                    ReinviteUsers(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        dynamodb_client=DynamodbClient(),
                    ).run(event=event)

                case "list_custom_groups":
                    self.__logger.info(f"Handling event {event_name} with ListCustomGroups")
                    ListCustomGroups(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        user_management_api=self._get_user_management_api(),
                    ).run(event=event)

                case "list_collection_items":
                    self.__logger.info(f"Handling event {event_name} with ListCollectionItems")
                    ListCollectionItems(
                        bitwarden_vault_client=bitwarden_vault_client,
                    ).run(event=event)

                case "update_collection_external_ids":
                    self.__logger.info(f"Handling event {event_name} with UpdateCollectionExternalIds")
                    UpdateCollectionExternalIds(
                        bitwarden_api=self._get_bitwarden_public_api(),
                        bitwarden_vault_client=bitwarden_vault_client,
                        s3_client=S3Client(),
                    ).run(event=event)

                case _:
                    self.__logger.info(f"Ignoring unknown event '{event_name}'")

        except BitwardenVaultClientLoginError as e:
            self.__logger.warning(f"Failed to complete {event_name} due to Bitwarden CLI login error - {e}")
        except BitwardenUserAlreadyExistsException as e:
            self.__logger.warning(f"Failed to complete {event_name} due to user already exists - {e}")

        finally:
            bitwarden_vault_client.logout()

    def _api_run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        self.__logger.debug("%s", event)
        validate(instance=event, schema=event_schema)
        request_path = event.get("path")

        match request_path:
            case "/bitwarden-manager/users":
                http_method = event.get("httpMethod")
                if http_method == "GET":
                    self.__logger.info(f"Handling path {request_path} with GetUserDetails")
                    return GetUserDetails(bitwarden_api=self._get_bitwarden_public_api()).run(event=event)
                else:
                    self.__logger.info(f"Ignoring unknown request method '{request_path}:{http_method}'")
                    return {
                        "statusCode": 501,
                        "body": json.dumps(f"Unknown request method for path '{request_path}:{http_method}'"),
                    }
            case _:
                self.__logger.info(f"Ignoring unknown request path '{request_path}'")
                return {"statusCode": 404, "body": json.dumps(f"Unknown request path '{request_path}'")}

    def _is_sqs_event(self, event: Dict[str, Any]) -> bool:
        return "eventSource" in event.get("Records", [{}])[0] and event["Records"][0]["eventSource"] == "aws:sqs"

    def _get_allowed_email_domains(self) -> list[str]:
        domain_list = os.environ.get("ALLOWED_DOMAINS", "").split(",")

        if domain_list == [""]:
            return []
        else:
            return list(map(lambda txt: txt.strip(), domain_list))

    def _get_bitwarden_cli_timeout(self) -> float:
        timeout = os.environ.get("BITWARDEN_CLI_TIMEOUT", "20")

        if timeout.isnumeric():
            return float(timeout)
        return 20.0

    def _get_bitwarden_public_api(self) -> BitwardenPublicApi:
        return BitwardenPublicApi(
            logger=self.__logger,
            client_id=self._get_secret("api-client-id"),
            client_secret=self._get_secret("api-client-secret"),
        )

    def _get_bitwarden_vault_client(self) -> BitwardenVaultClient:
        return BitwardenVaultClient(
            logger=self.__logger,
            client_id=self._get_secret("vault-client-id"),
            client_secret=self._get_secret("vault-client-secret"),
            password=self._get_secret("vault-password"),
            export_enc_password=self._get_secret("export-encryption-password"),
            cli_executable_path="bw",
            organisation_id=self._get_secret("organisation-id"),
            cli_timeout=self._get_bitwarden_cli_timeout(),
        )

    def _get_secret(self, secret_id: str) -> str:
        return self._secretsmanager.get_secret_value(f"/bitwarden/{secret_id}")

    def _get_user_management_api(self) -> UserManagementApi:
        return UserManagementApi(
            logger=self.__logger,
            client_id=self._get_secret("ldap-username"),
            client_secret=self._get_secret("ldap-password"),
        )
