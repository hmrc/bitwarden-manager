import boto3

from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict, Any


class DynamodbClient:
    def __init__(self) -> None:
        self._boto_dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")

    def write_item_to_table(self, table_name: str, item: Dict[str, Any]) -> None:
        try:
            table = self._boto_dynamodb.Table(table_name)
            table.put_item(Item=item)
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to write to DynamoDB", e) from e
