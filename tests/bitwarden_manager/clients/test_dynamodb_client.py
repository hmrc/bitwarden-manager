import boto3
import pytest
from datetime import datetime
from boto3_type_annotations import dynamodb
from moto import mock_dynamodb

from bitwarden_manager.clients.dynamodb_client import DynamodbClient


@mock_dynamodb  # type: ignore
def test_write_item_to_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, table_name)
    client.write_item_to_table(table_name=table_name, item=item)
    table = dynamodb.Table(table_name)
    assert table.get_item(Key={"username": "test.user"})["Item"] == item


def create_table_in_local_region(dynamodb: dynamodb.Client, table_name: str) -> None:
    dynamodb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
    )


def test_failed_to_write_item_to_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden2"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date}
    with pytest.raises(Exception, match="Failed to write to DynamoDB"):
        client.write_item_to_table(table_name=table_name, item=item)
