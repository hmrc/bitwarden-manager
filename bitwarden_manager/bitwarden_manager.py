import boto3

from bitwarden_manager.clients.aws_secretsmanager_client import AwsSecretsManagerClient
from bitwarden_manager.redacting_formatter import get_bitwarden_logger


class BitwardenManager:
    def __init__(self) -> None:
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))

    def get_ldap_username(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-username")

    def get_ldap_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-password")

    def run(self) -> None:
        logger = get_bitwarden_logger()
        logger.info(f"retrieved ldap creds with username {self.get_ldap_username()}")

        # test log line please remove once we have some real things to do
        logger.info("testing CLIENT_ID organization.KPL8P83fWXAvYvNYcbNWAKAcdNmn4Ssgne7w")
