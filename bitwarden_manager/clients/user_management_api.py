from logging import Logger
from typing import Dict, Any, List
from urllib.parse import quote
from requests import get, post, HTTPError, Timeout

REQUEST_TIMEOUT_SECONDS = 5

API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
AUTH_URL = "https://user-management-auth-production.tools.tax.service.gov.uk/v1/login"


class UserManagementApi:
    def __init__(self, logger: Logger, client_id: str, client_secret: str) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id

    def get_user_teams(self, username: str) -> List[str]:
        user_teams = []
        bearer = self.__fetch_token()
        response = get(
            f"{API_URL}/organisations/users/{username}/teams",
            headers={
                "Token": bearer,
                "requester": self.__client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            if response.status_code == 404 and response.json().get("reason", None) == "Not Found":
                self.__logger.info("User Not Found")
            elif response.status_code == 422 and response.json().get("reason", None) == "Invalid uid":
                self.__logger.info("Invalid User")
            else:
                raise Exception("Failed to get teams for user", response.content, e) from e
        response_json: Dict[str, Any] = response.json()
        if response_json.get("teams"):
            for team in response_json.get("teams", {}):
                user_teams.append(team.get("team", ""))
        self.__logger.info(f"User teams: {user_teams}")
        return user_teams

    def get_user_role_by_team(self, username: str, team: str) -> str:
        bearer = self.__fetch_token()
        try:
            response = get(
                f"{API_URL}/organisations/teams/{quote(team)}/members",
                headers={
                    "Token": bearer,
                    "requester": self.__client_id,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Timeout:
            raise Exception(f"Failed to get team members of {team} for {username} before the timeout")

        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception(f"Failed to get team members of {team}", response.content, e) from e

        response_json: Dict[str, Any] = response.json()
        roles: List[str] = [m["role"] for m in response_json.get("members", []) if m["username"] == username]
        if len(roles) == 0:
            raise Exception(f"{username} is not a member of {team}")

        return roles[0]

    def get_teams(self) -> List[str]:
        bearer = self.__fetch_token()
        response = get(
            f"{API_URL}/organisations/teams",
            headers={
                "Token": bearer,
                "requester": self.__client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception("Failed to get teams", response.content, e) from e
        response_json: Dict[str, Any] = response.json()
        return [t.get("team") for t in response_json.get("teams", [])]

    def __fetch_token(self) -> str:
        response = post(
            AUTH_URL,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json={
                "username": self.__client_id,
                "password": self.__client_secret,
            },
            timeout=15,
        )
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception(f"Failed to authenticate with {AUTH_URL}, creds incorrect?", e) from e

        response_json: Dict[str, str] = response.json()
        return response_json.get("Token", "")
