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

    def delete_item_from_table(self, table_name: str, key: Dict[str, Any]) -> None:
        try:
            table = self._boto_dynamodb.Table(table_name)
            table.delete_item(Key=key)
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to delete from DynamoDB", e) from e

    def get_item_from_table(self, table_name: str, key: Dict[str, Any]) -> Any:
        try:
            table = self._boto_dynamodb.Table(table_name)
            resp = table.get_item(Key=key)
            item = resp.get("Item", None)
            return item
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to read from DynamoDB", e) from e

    def update_item_in_table(self, table_name: str, key: Dict[str, Any], reinvites: int, total_invites: int) -> None:
        try:
            table = self._boto_dynamodb.Table(table_name)
            table.update_item(
                Key=key,
                UpdateExpression="set reinvites=:r",
                ExpressionAttributeValues={":r": reinvites},
                ReturnValues="UPDATED_NEW",
            )
            table.update_item(
                Key=key,
                UpdateExpression="set total_invites=:t",
                ExpressionAttributeValues={":t": total_invites},
                ReturnValues="UPDATED_NEW",
            )
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to update item in DynamoDB", e) from e
