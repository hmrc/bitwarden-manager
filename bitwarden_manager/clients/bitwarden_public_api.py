import base64
from logging import Logger
from typing import Dict, List, Any, Optional

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

    @staticmethod
    def external_id_base64_encoded(id: str) -> str:
        return base64.b64encode(id.encode()).decode("utf-8")

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
        external_id: str = response.json().get("externalId", "")
        # All groups created by automation have an external id. Manually created
        # groups _may_ have an external id but we assume that in general they don't
        # since you cannot add one through the UI - only through the API
        return not bool(external_id and external_id.strip())

    def __collection_manually_created(self, collection_id: str) -> bool:
        response = session.get(f"{API_URL}/collections/{collection_id}")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get collections", response.content, error) from error
        external_id: str = response.json().get("externalId", "")
        # All collections created by automation have an external id. Manually created
        # collections _may_ have an external id but we assume that in general they don't
        # since you cannot add one through the UI - only through the API
        return not bool(external_id and external_id.strip())

    def __fetch_user_id(self, email: Optional[str] = None, external_id: Optional[str] = None) -> str:
        response = session.get(f"{API_URL}/members")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to retrieve users", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        for user in response_json.get("data", ""):
            if external_id and external_id == user.get("externalId", ""):
                return str(user.get("id", ""))
            if email and email == user.get("email", ""):
                return str(user.get("id", ""))
        return ""

    def __fetch_user_id_by_email(self, email: str) -> str:
        return self.__fetch_user_id(email=email)

    def __fetch_user_id_by_external_id(self, external_id: str) -> str:
        return self.__fetch_user_id(external_id=external_id)

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

    def __get_collection(self, collection_id: str) -> Dict[str, Any]:
        response = session.get(f"{API_URL}/collections/{collection_id}")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get collection", response.content, error) from error
        response_json: Dict[str, str] = response.json()
        return response_json

    def __get_collection_groups(self, collection_id: str) -> set[str]:
        group_ids = {group.get("id", "") for group in self.__get_collection(collection_id).get("groups", "")}
        return group_ids

    def __get_collection_external_id(self, collection_id: str) -> str:
        return self.__get_collection(collection_id).get("externalId", "")

    def __update_collection_external_id(self, collection_id: str, external_id: str) -> None:
        response = session.put(
            f"{API_URL}/collections/{collection_id}",
            json={
                "externalId": external_id,
                "groups": self.__get_collection(collection_id).get("groups", []),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update external id of collection: {collection_id}") from error

    def __list_collections(self) -> List[Dict[str, Any]]:
        response = session.get(f"{API_URL}/collections")
        try:
            response.raise_for_status()
            response_json: Dict[str, Any] = response.json()
            return response_json.get("data", [])
        except HTTPError as error:
            raise Exception("Failed to list collections", response.content, error) from error

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
                self.__logger.info("User already invited ignoring error")
                return self.__fetch_user_id_by_email(email)
            raise Exception("Failed to invite user", response.content, error) from error

        self.__logger.info("User has been invited to Bitwarden")
        response_json: Dict[str, str] = response.json()
        return response_json.get("id", "")

    def remove_user(self, username: str) -> None:
        self.__fetch_token()
        id = self.__fetch_user_id_by_external_id(external_id=username)
        if not id:
            self.__logger.info(f"User {username} not found in the Bitwarden organisation")
            return

        response = session.delete(
            f"{API_URL}/members/{id}",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to delete user {username}", response.content, error) from error

        self.__logger.info(f"User {username} has been removed from the Bitwarden organisation")

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
                "externalId": self.external_id_base64_encoded(group_name),
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
        if self.__collection_manually_created(collection_id):
            return
        group_ids = self.__get_collection_groups(collection_id)
        if group_id in group_ids:
            self.__logger.info(f"Group already assigned to collection: {collection_name}")
            return
        group_ids.add(group_id)
        group_json = [{"id": group_id, "readOnly": False} for group_id in group_ids]

        try:
            put_response = session.put(
                f"{API_URL}/collections/{collection_id}",
                json={
                    "externalId": self.__get_collection_external_id(collection_id),
                    "groups": group_json,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            self.__logger.info(f"Group assigned to collection: {collection_name}")
            put_response.raise_for_status()
        except HTTPError as error:
            http_error_msg = error.response.json().get("error", "")
            if "Failed to update the collection groups" in http_error_msg:
                raise Exception("Failed to update the collection groups") from error

    def list_existing_collections(self, teams: List[str]) -> Dict[str, Dict[str, str]]:
        collections: Dict[str, Dict[str, str]] = {}
        for collection_object in self.__list_collections():
            print("DEBUG", self.__list_collections())
            for team in teams:
                external_id_base64_encoded = self.external_id_base64_encoded(team)
                if collection_object.get("externalId", "") == external_id_base64_encoded:
                    if not collections.get(team):
                        collections[team] = {
                            "id": collection_object.get("id"),
                            "externalId": external_id_base64_encoded,
                        }
                    else:
                        collections[team] = {"id": "duplicate", "externalId": external_id_base64_encoded}
        return collections

    def collate_user_group_ids(
        self, teams: List[str], groups: Dict[str, str], collections: Dict[str, Dict[str, str]]
    ) -> List[str]:
        groups_ids = []
        for team in teams:
            collection = collections.get(team, {})
            if collection:
                collection_id = collection.get("id", "")
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

    def update_all_team_collection_external_ids(self, teams: List[str]) -> None:
        for collection_object in self.__list_collections():
            self.update_collection_external_id_to_encoded_team_name(collection_object, teams)

    def update_collection_external_id_to_encoded_team_name(
        self, collection_object: Dict[str, Any], teams: List[str]
    ) -> None:
        for team in teams:
            if collection_object.get("externalId") == team:
                self.__update_collection_external_id(collection_object.get("id"), self.external_id_base64_encoded(team))
                self.__logger.info(f"Updated external id of collection: {team}")
