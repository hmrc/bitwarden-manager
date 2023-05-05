from botocore.exceptions import BotoCoreError, ClientError
import boto3


class AwsSecretsManagerClient():
    """docstring for AwsSecretsManagerClient."""
    def __init__(self):
        self._secretsmanager = boto3.client('secretsmanager', region_name='eu-west-2')

    def get_secret_value(self, secret_id: str) -> str:
        try:
            return self._secretsmanager.get_secret_value(SecretId=secret_id)['SecretString']
        except (BotoCoreError, ClientError) as err:
            raise err
