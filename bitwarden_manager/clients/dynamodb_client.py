import boto3

from botocore.exceptions import BotoCoreError, ClientError
from typing import Dict, Any


class DynamodbClient:
    _table_name: str = "bitwarden"

    def __init__(self) -> None:
        self._client = boto3.client("dynamodb", region_name="eu-west-2")

    def add_item_to_table(self, item: Dict[str, Any]) -> None:
        try:
            self._client.put_item(
                TableName=self._table_name,
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

    def delete_item_from_table(self, username: str) -> None:
        try:
            self._client.delete_item(
                TableName=self._table_name,
                Key={
                    "username": {
                        "S": username,
                    }
                },
            )
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to delete from DynamoDB", e) from e

    def get_item_from_table(self, username: str) -> Dict[str, Any] | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key={
                    "username": {
                        "S": username,
                    }
                },
                ProjectionExpression="username, invite_date, reinvites, total_invites",
            )

            item = response.get("Item", None)
            if item:
                return {
                    "username": item.get("username", {}).get("S"),
                    "invite_date": item.get("invite_date", {}).get("S"),
                    "reinvites": int(item.get("reinvites", {}).get("N")),
                    "total_invites": int(item.get("total_invites", {}).get("N", 0)),
                }

            return None
        except (BotoCoreError, ClientError) as e:
            raise Exception("Failed to read from DynamoDB", e) from e

    def update_item_in_table(self, username: str, item: Dict[Any, Any]) -> None:
        try:
            self._client.update_item(
                TableName=self._table_name,
                Key={
                    "username": {
                        "S": username,
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
