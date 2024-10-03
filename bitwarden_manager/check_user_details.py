from jsonschema import validate
from typing import Dict, Any
from bitwarden_manager.clients.bitwarden_public_api import BitwardenPublicApi
from bitwarden_manager.clients.bitwarden_vault_client import BitwardenVaultClient

check_user_event_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "path of request",
            "pattern": "/bitwarden-manager/check-user",
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


class CheckUserDetails:
    def __init__(
        self,
        bitwarden_api: BitwardenPublicApi,
        bitwarden_vault_client: BitwardenVaultClient,
    ):
        self.bitwarden_api = bitwarden_api
        self.bitwarden_vault_client = bitwarden_vault_client

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        validate(instance=event, schema=check_user_event_schema)
        username = event["queryStringParameters"]["username"]
        user_details = self.bitwarden_api.get_user_by_username(username=username)
        return user_details


# {
#   "object": "member",
#   "id": "4dd808ea-6929-47f9-818e-b17f00f834a4",
#   "userId": null,
#   "name": null,
#   "email": "andy.waddams+bitwarden@digital.hmrc.gov.uk",
#   "twoFactorEnabled": false,
#   "status": 0,
#   "collections": [],
#   "type": 1,
#   "externalId": null,
#   "resetPasswordEnrolled": false,
#   "permissions": null
# }

# my_path = event["path"]
# event_name = event["path"].replace("/", " ").replace("?", " ").replace("-", "_").split()[-1]
# try:
#     match event_name:
#         case "check-user":
#             username = {"username": event["queryStringParameters"]["username"]}
#             path = {"path": event["path"]}
#             get_user_event = dict(username)
#             get_user_event.update(path)
#             return {
#                 'statusCode': 200,
#                 'body': json.dumps(get_user_event)
#             }
# except:
#     return {
#         'statusCode': 404,
#         'body': json.dumps("Event not found: " + event_name)
#     }
