import boto3
import pytest
from datetime import datetime
from boto3_type_annotations import dynamodb
from moto import mock_aws

from bitwarden_manager.clients.dynamodb_client import DynamodbClient

TABLE_NAME = "bitwarden"


def create_table_in_local_region(dynamodb: dynamodb.Client, table_name: str) -> None:
    dynamodb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
    )


@mock_aws
def test_add_item_to_table() -> None:
    client = DynamodbClient()

    item = {
        "username": "test.user",
        "invite_date": datetime.today().strftime("%Y-%m-%d"),
        "reinvites": 0,
        "total_invites": 1,
    }

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, TABLE_NAME)
    table = dynamodb.Table(TABLE_NAME)

    assert table.scan().get("Count") == 0
    client.add_item_to_table(item=item)
    assert table.scan().get("Count") == 1
    assert table.get_item(Key={"username": "test.user"})["Item"] == item


@mock_aws
def test_delete_item_from_table() -> None:
    client = DynamodbClient()

    item = {
        "username": "test.user",
        "invited_date": datetime.today().strftime("%Y-%m-%d"),
        "reinvites": 0,
        "total_invites": 1,
    }

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, TABLE_NAME)
    table = dynamodb.Table(TABLE_NAME)

    assert table.scan().get("Count") == 0
    table.put_item(Item=item)
    assert table.scan().get("Count") == 1
    client.delete_item_from_table(username=str(item["username"]))
    assert table.scan().get("Count") == 0


@mock_aws
def test_get_item_from_table() -> None:
    client = DynamodbClient()

    item = {
        "username": "test.user",
        "invite_date": datetime.today().strftime("%Y-%m-%d"),
        "reinvites": 0,
        "total_invites": 1,
    }

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, TABLE_NAME)
    table = dynamodb.Table(TABLE_NAME)

    table.put_item(Item=item)
    assert client.get_item_from_table(username="test.user") == item
    assert client.get_item_from_table(username="missing.user") is None


@mock_aws
def test_update_item_in_table() -> None:
    client = DynamodbClient()

    dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
    create_table_in_local_region(dynamodb, TABLE_NAME)
    table = dynamodb.Table(TABLE_NAME)

    date = datetime.today().strftime("%Y-%m-%d")
    username = "test.user"

    add_item = {"username": username, "invite_date": date, "reinvites": 1, "total_invites": 2}
    edit_item = {"username": username, "invite_date": date, "reinvites": 2, "total_invites": 3}

    table.put_item(Item=add_item)
    client.update_item_in_table(username=username, item=edit_item)
    assert client.get_item_from_table(username=username) == edit_item


def test_failed_to_add_item_to_table() -> None:
    client = DynamodbClient()

    with pytest.raises(Exception, match="Failed to add item to DynamoDB"):
        client.add_item_to_table(
            item={
                "username": "test.user",
                "invite_date": datetime.today().strftime("%Y-%m-%d"),
                "reinvites": 0,
                "total_invites": 1,
            },
        )


def test_failed_to_delete_item_from_table() -> None:
    client = DynamodbClient()

    with pytest.raises(Exception, match="Failed to delete from DynamoDB"):
        client.delete_item_from_table(username="test.user")


def test_failed_to_get_item_from_table() -> None:
    client = DynamodbClient()

    with pytest.raises(Exception, match="Failed to read from DynamoDB"):
        client.get_item_from_table(username="test.user")


def test_failed_to_update_item_in_table() -> None:
    client = DynamodbClient()

    with pytest.raises(Exception, match="Failed to update item in DynamoDB"):
        client.update_item_in_table(
            username="test.user",
            item={
                "invite_date": datetime.today().strftime("%Y-%m-%d"),
                "reinvites": 0,
                "total_invites": 1,
            },
        )
