import boto3

from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict, Any


class DynamodbClient:
    def __init__(self) -> None:
        self._boto_dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        self.client = boto3.client("dynamodb", region_name="eu-west-2")

    def write_item_to_table(self, table_name: str, item: Dict[str, Any]) -> None:
        try:
            table = self._boto_dynamodb.Table(table_name)
            table.put_item(Item=item)
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to write to DynamoDB", e) from e

    def add_item_to_table(self, table_name: str, item: Dict[str, Any]) -> None:
        try:
            self.client.put_item(
                TableName=table_name,
                Item={
                    "username": {
                        "S": item.get("username"),
                    },
                    "invite_date": {
                        "S": item.get("invite_date"),
                    },
                    "reinvites": {
                        "N": str(item.get("reinvites")),
                    },
                    "total_invites": {
                        "N": str(item.get("total_invites")),
                    },
                },
            )
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to add item to DynamoDB", e) from e

    def delete_item_from_table(self, table_name: str, key: Dict[str, Any]) -> None:
        try:
            table = self._boto_dynamodb.Table(table_name)
            table.delete_item(Key=key)
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to delete from DynamoDB", e) from e

    def get_item_from_table(self, table_name: str, key: Dict[str, Any]) -> Any:
        try:
            table = self._boto_dynamodb.Table(table_name)
            resp = table.get_item(
                Key=key,
            )

            return resp.get("Item", None)
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to read from DynamoDB", e) from e

    def update_item_in_table(self, table_name: str, key: Dict[str, Any], item: Dict[Any, Any]) -> None:
        try:
            self.client.update_item(
                TableName=table_name,
                Key={
                    "username": {
                        "S": key.get("username"),
                    }
                },
                AttributeUpdates={
                    "invite_date": {
                        "Value": {
                            "S": item.get("invite_date"),
                        }
                    },
                    "reinvites": {
                        "Value": {
                            "N": str(item.get("reinvites")),
                        }
                    },
                    "total_invites": {
                        "Value": {
                            "N": str(item.get("total_invites")),
                        }
                    },
                },
            )
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to update item in DynamoDB", e) from e
