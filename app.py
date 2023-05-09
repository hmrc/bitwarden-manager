# import boto3
# from botocore.exceptions import ClientError
import subprocess


def handler(event, context):
    domain = input("Enter the Domain: ")
    subprocess.check_output(f"nslookup {domain}", shell=True, encoding='UTF-8')
