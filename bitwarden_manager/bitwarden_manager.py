import boto3

from bitwarden_manager.aws_secretsmanager_client import AwsSecretsManagerClient


class BitwardenManager:
    def __init__(self) -> None:
        self._secretsmanager = AwsSecretsManagerClient(secretsmanager_client=boto3.client("secretsmanager"))

    def get_ldap_username(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-username")

    def get_ldap_password(self) -> str:
        return self._secretsmanager.get_secret_value("/bitwarden/ldap-password")

    def run(self) -> None:
        pass
