import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    print("event: {}".format(event))
