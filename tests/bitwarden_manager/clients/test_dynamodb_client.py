import boto3
import pytest
from datetime import datetime
from boto3_type_annotations import dynamodb
from moto import mock_aws

from bitwarden_manager.clients.dynamodb_client import DynamodbClient


def create_table_in_local_region(dynamodb: dynamodb.Client, table_name: str) -> None:
    dynamodb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
    )


@mock_aws
def test_write_item_to_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date, "reinvites": 0}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, table_name)
    table = dynamodb.Table(table_name)
    assert table.scan().get("Count") == 0
    client.write_item_to_table(table_name=table_name, item=item)
    assert table.scan().get("Count") == 1
    key = {"username": "test.user"}
    assert table.get_item(Key=key)["Item"] == item


@mock_aws
def test_delete_item_from_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date, "reinvites": 0, "total_invites": 1}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, table_name)
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)
    assert table.scan().get("Count") == 1
    key = {"username": "test.user"}
    client.delete_item_from_table(table_name=table_name, key=key)
    assert table.scan().get("Count") == 0


@mock_aws
def test_get_item_from_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date, "reinvites": 0, "total_invites": 1}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, table_name)
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)
    key = {"username": "test.user"}
    assert client.get_item_from_table(table_name=table_name, key=key) == item
    assert client.get_item_from_table(table_name=table_name, key={"username": "missing.user"}) is None


@mock_aws
def test_update_item_in_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date, "reinvites": 0, "total_invites": 1}
    updated_item = {"username": "test.user", "date": date, "reinvites": 1, "total_invites": 2}

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, table_name)
    table = dynamodb.Table(table_name)
    table.put_item(Item=item)
    key = {"username": "test.user"}
    client.update_item_in_table(table_name=table_name, key=key, reinvites=1, total_invites=2)
    assert client.get_item_from_table(table_name=table_name, key=key) == updated_item


def test_failed_to_write_item_to_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    date = datetime.today().strftime("%Y-%m-%d")
    item = {"username": "test.user", "date": date, "reinvites": 0}
    with pytest.raises(Exception, match="Failed to write to DynamoDB"):
        client.write_item_to_table(table_name=table_name, item=item)


def test_failed_to_delete_item_from_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    key = {"username": "test.user"}
    with pytest.raises(Exception, match="Failed to delete from DynamoDB"):
        client.delete_item_from_table(table_name=table_name, key=key)


def test_failed_to_get_item_from_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    key = {"username": "test.user"}
    with pytest.raises(Exception, match="Failed to read from DynamoDB"):
        client.get_item_from_table(table_name=table_name, key=key)


def test_failed_to_update_item_in_table() -> None:
    client = DynamodbClient()

    table_name = "bitwarden"
    key = {"username": "test.user"}
    with pytest.raises(Exception, match="Failed to update item in DynamoDB"):
        client.update_item_in_table(table_name=table_name, key=key, reinvites=1, total_invites=2)
