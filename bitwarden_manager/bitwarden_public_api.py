from requests import post, HTTPError

LOGIN_URL = "https://identity.bitwarden.com/connect/token"
API_URL = "https://api.bitwarden.com/public"


class BitwardenPublicApi:
    def __init__(self, client_id, client_secret):
        self.__client_secret = client_secret
        self.__client_id = client_id

    def invite_user(self, username, email):
        bearer = self.__fetch_token()
        response = post(
            f"{API_URL}/members",
            headers={"Authorization": f"Bearer {bearer}"},
            json={
                "type": 2,
                "accessAll": False,
                "resetPasswordEnrolled": True,
                "externalId": username,
                "email": email,
                "collections": [],
            },
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception(f"Failed to invite user", e) from e

    def __fetch_token(self):
        response = post(
            LOGIN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": "api.organization",
                "client_id": self.__client_id,
                "client_secret": self.__client_secret,
            },
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception(
                f"Failed to authenticate with {LOGIN_URL}, creds incorrect?", e
            ) from e
        return response.json()["access_token"]
