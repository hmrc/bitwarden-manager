from unittest import mock

from app import handler


@mock.patch("boto3.client")
def test_handler(boto3_mock):
    handler(event={}, context={})
