from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict
import boto3


class AwsSecretsManagerClient:
    """docstring for AwsSecretsManagerClient."""

    def __init__(self) -> None:
        self._secretsmanager = boto3.client("secretsmanager", region_name="eu-west-2")

    def get_secret_value(self, secret_id: str) -> str:
        try:
            value: Dict[str, str] = self._secretsmanager.get_secret_value(SecretId=secret_id)
        except (BotoCoreError, ClientError) as err:
            raise Exception(f"failed to fetch secret value from id: '{secret_id}'", err) from err

        return value["SecretString"]
