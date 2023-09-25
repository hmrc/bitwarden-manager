from logging import Logger
from typing import Dict, List, Any

from requests import HTTPError, Session

REGULAR_USER = 2
REQUEST_TIMEOUT_SECONDS = 30

LOGIN_URL = "https://identity.bitwarden.com/connect/token"
API_URL = "https://api.bitwarden.com/public"

session = Session()


class BitwardenPublicApi:
    def __init__(self, logger: Logger, client_id: str, client_secret: str) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id

    def __get_user_groups(self, user_id: str) -> List[str]:
        response = session.get(f"{API_URL}/members/{user_id}/group-ids")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get user groups", response.content, error) from error
        response_list: List[str] = response.json()
        return response_list

    def __group_manually_created(self, group_id: str) -> bool:
        response = session.get(f"{API_URL}/groups/{group_id}")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get group", response.content, error) from error
        external_id: str = response.json().get("externalId")
        # All groups created by automation have an external id. Manually created
        # groups _may_ have an external id but we assume that in general they don't
        return not bool(external_id and external_id.strip())

    def __fetch_user_id(self, email: str) -> str:
        response = session.get(f"{API_URL}/members")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to retrieve users", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        for user in response_json.get("data", ""):
            if email == user.get("email", ""):
                return str(user.get("id", ""))
        return ""

    def __fetch_token(self) -> str:
        response = session.post(
            LOGIN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": "api.organization",
                "client_id": self.__client_id,
                "client_secret": self.__client_secret,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to authenticate with {LOGIN_URL}, creds incorrect?", error) from error
        response_json: Dict[str, str] = response.json()
        access_token = response_json["access_token"]
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        return access_token

    def __get_collection_groups(self, collection_id: str) -> set[str]:
        response = session.get(f"{API_URL}/collections/{collection_id}")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get collections", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        group_ids = {group.get("id", "") for group in response_json.get("groups", "")}
        return group_ids

    def invite_user(self, username: str, email: str) -> str:
        self.__fetch_token()
        response = session.post(
            f"{API_URL}/members",
            json={
                "type": REGULAR_USER,
                "accessAll": False,
                "resetPasswordEnrolled": True,
                "externalId": username,
                "email": email,
                "collections": [],
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            if (
                response.status_code == 400
                and response.json().get("message", None) == "This user has already been invited."
            ):
                self.__logger.info("user already invited ignoring error")
                return self.__fetch_user_id(email)
            raise Exception("Failed to invite user", response.content, error) from error
        response_json: Dict[str, str] = response.json()
        return response_json.get("id", "")

    def list_existing_groups(self, users_teams: List[str]) -> Dict[str, str]:
        existing_groups: Dict[str, str] = {}
        response = session.get(f"{API_URL}/groups")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to list groups", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        for group in response_json.get("data", {}):
            if group.get("name", "") in users_teams:
                if not existing_groups.get(group.get("name")):
                    existing_groups[group.get("name")] = group.get("id")
                else:
                    existing_groups[group.get("name")] = "duplicate"
        return existing_groups

    def create_group(self, group_name: str, collection_id: str) -> str:
        if len(group_name) == 0 or len(group_name) > 100:
            self.__logger.info(f"Group name invalid: {group_name}")
            return ""

        json_id = []
        if collection_id:
            json_id.append({"id": collection_id, "readOnly": False})

        response = session.post(
            f"{API_URL}/groups",
            json={
                "name": group_name,
                "accessAll": False,
                "collections": json_id,
                "externalId": group_name,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to create group", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        return response_json.get("id", "")

    def associate_user_to_groups(self, user_id: str, group_ids: List[str]) -> None:
        existing_user_group_ids = self.__get_user_groups(user_id)
        user_group_ids = existing_user_group_ids[:]
        for group_id in group_ids:
            if group_id not in user_group_ids and not self.__group_manually_created(group_id):
                user_group_ids.append(group_id)
        if not existing_user_group_ids == user_group_ids:
            response = session.put(
                f"{API_URL}/members/{user_id}/group-ids",
                json={"groupIds": user_group_ids},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            try:
                response.raise_for_status()
            except HTTPError as error:
                raise Exception("Failed to associate user to group-ids", response.content, error) from error

    def update_collection_groups(self, collection_name: str, collection_id: str, group_id: str) -> None:
        group_ids = self.__get_collection_groups(collection_id)
        if group_id in group_ids:
            self.__logger.info("Group already exists in collection")
            return
        group_ids.add(group_id)
        group_json = [{"id": group_id, "readOnly": False} for group_id in group_ids]
        response = session.put(
            f"{API_URL}/collections/{collection_id}",
            json={
                "externalId": collection_name,
                "groups": group_json,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to associate collection to group-ids", response.content, error) from error

    def list_existing_collections(self, teams: List[str]) -> Dict[str, str]:
        collections: Dict[str, str] = {}
        response = session.get(f"{API_URL}/collections")
        try:
            response.raise_for_status()
            response_json: Dict[str, Any] = response.json()
            for collection_object in response_json.get("data", {}):
                if collection_object.get("externalId", "") in teams:
                    if not collections.get(collection_object.get("externalId")):
                        collections[collection_object.get("externalId")] = collection_object.get("id")
                    else:
                        collections[collection_object.get("externalId")] = "duplicate"
            return collections
        except HTTPError as error:
            raise Exception("Failed to list collections", response.content, error) from error

    def collate_user_group_ids(
        self, teams: List[str], groups: Dict[str, str], collections: Dict[str, str]
    ) -> List[str]:
        groups_ids = []
        for team in teams:
            collection_id = collections.get(team, "")
            group_id = groups.get(team, "")
            if "duplicate" not in (group_id, collection_id):
                if not group_id:
                    group_id = self.create_group(group_name=team, collection_id=collection_id)
                if collection_id and group_id:
                    self.update_collection_groups(team, collection_id, group_id)
                groups_ids.append(group_id)
            else:
                raise Exception(f"There are duplicate groups or collections for {team}")
        return groups_ids
