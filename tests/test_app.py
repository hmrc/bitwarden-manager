from unittest import mock
from unittest.mock import Mock

from app import handler


@mock.patch("boto3.client")
def test_handler(boto3_mock: Mock) -> None:
    handler(event={}, context={})
