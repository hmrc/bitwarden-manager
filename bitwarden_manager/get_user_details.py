import json
from jsonschema import validate
from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi, BitwardenUserNotFoundException
from bitwarden_manager.redacting_formatter import get_bitwarden_logger
from bitwarden_manager.user import BitwardenUserResponse

check_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "path of request",
            "pattern": "/bitwarden-manager/users",
        },
        "queryStringParameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "the users ldap username"},
            },
            "required": ["username"],
        },
    },
    "required": ["path"],
}


class GetUserDetails:
    def __init__(self, bitwarden_api: BitwardenPublicApi):
        self.bitwarden_api = bitwarden_api
        self.__logger = get_bitwarden_logger(extra_redaction_patterns=[])

    def get_user(self, username: str) -> Dict[str, Any]:
        try:
            user_response = BitwardenUserResponse(self.bitwarden_api.get_user_by_username(username=username))

            return {
                "statusCode": 200,
                "headers": {},
                "body": json.dumps(user_response.user_response()),
            }
        except BitwardenUserNotFoundException as e:
            self.__logger.warning(str(e))
            response = {
                "statusCode": 404,
                "headers": {},
                "body": json.dumps({"ERROR": f"Username {username} not found"}),
            }
            self.__logger.info(json.dumps(response))
            return response

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        validate(instance=event, schema=check_user_event_schema)
        username = event["queryStringParameters"]["username"]
        self.__logger.info(f"Fetching user details for {username}")
        return self.get_user(username=username)
