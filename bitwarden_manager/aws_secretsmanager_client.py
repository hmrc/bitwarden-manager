from boto3_type_annotations.secretsmanager.client import Client
from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict


class AwsSecretsManagerClient:
    """docstring for AwsSecretsManagerClient."""

    def __init__(self, secretsmanager_client: Client) -> None:
        self._secretsmanager = secretsmanager_client

    def get_secret_value(self, secret_id: str) -> str:
        try:
            value: Dict[str, str] = self._secretsmanager.get_secret_value(SecretId=secret_id)
        except (BotoCoreError, ClientError) as err:
            raise Exception(f"failed to fetch secret value from id: '{secret_id}'", err) from err

        return value["SecretString"]
