import base64
import datetime
import time
from logging import Logger
from typing import Dict, List, Any, Optional

from requests import HTTPError, Session

from bitwarden_manager.user import UmpUser, UserStatus, UserType


REQUEST_TIMEOUT_SECONDS = 30

LOGIN_URL = "https://identity.bitwarden.eu/connect/token"
API_URL = "https://api.bitwarden.eu/public"

session = Session()


class BitwardenUserNotFoundException(Exception):
    pass


class BitwardenUserAlreadyExistsException(Exception):
    pass


class BitwardenAPIException(Exception):
    pass


class BitwardenPublicApi:

    bitwarden_access_token = None

    def __init__(self, logger: Logger, client_id: str, client_secret: str) -> None:
        self.__logger = logger
        self.__client_secret = client_secret
        self.__client_id = client_id

    @staticmethod
    def external_id_base64_encoded(id: str) -> str:
        return base64.b64encode(id.encode()).decode("utf-8")

    def __get_user_collections(self, user_collections: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if user_collections is None:
            return []

        collections: List[Dict[str, Any]] = []
        for collection in user_collections:
            response = session.get(f"{API_URL}/collections/{collection.get('id')}")
            try:
                response.raise_for_status()
            except HTTPError as error:
                raise Exception("Failed to get collection", response.content, error) from error
            collections.append(response.json())

        return collections

    def __get_user_groups(self, user_id: str) -> List[str]:
        response = session.get(f"{API_URL}/members/{user_id}/group-ids")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get user groups", response.content, error) from error
        response_list: List[str] = response.json()
        return response_list

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

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        self.__fetch_token()
        for user in self.get_users():
            if email and email == user.get("email", ""):
                return user
        else:
            raise BitwardenUserNotFoundException(f"No user with email {email} found")

    def get_user_by_username(self, username: str) -> Dict[str, Any]:
        self.__fetch_token()
        for user in self.get_users():
            if username and username in user.get("email", ""):
                return user
        else:
            raise BitwardenUserNotFoundException(f"No user with username {username} found")

    def get_user_by_external_id(self, external_id: str) -> Dict[str, Any]:
        self.__fetch_token()
        for user in self.get_users():
            if external_id and external_id == user.get("externalId", ""):
                return user
        else:
            raise BitwardenUserNotFoundException(f"No user with external_id {external_id} found")

    @staticmethod
    def get_users() -> List[Dict[str, Any]]:
        response = session.get(f"{API_URL}/members", timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to retrieve users", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        return list(response_json.get("data", []))

    def get_user_by(self, field: str, value: str) -> Dict[str, Any]:
        self.__fetch_token()
        for user in self.get_users():
            if value and value in user.get(field, ""):
                return user
        else:
            raise BitwardenUserNotFoundException(f"No user with {field} {value} found")

    def fetch_user_id_by_email(self, email: str) -> str:
        return str(self.get_user_by_email(email=email)["id"])

    def fetch_user_id_by_external_id(self, external_id: str) -> str:
        return str(self.get_user_by_external_id(external_id=external_id)["id"])

    def get_active_user_report(self, duration_days: int = 35) -> set[str]:
        """
        Retrieves a report of active users from Bitwarden within the previous specified duration in days.

        Args:
            duration_days (int): The number of days to consider for user activity. Defaults to 35 days.

        Returns:
            set[str]: A set of active user ids.
        """
        self.__fetch_token()
        start_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=duration_days)).strftime(
            "%Y-%m-%d"
        )

        all_events = self._get_events(start_date)

        active_ids = set()

        for event in all_events:
            if event.get("actingUserId", None):
                active_ids.add(event.get("actingUserId", ""))

        return active_ids

    def _get_events(self, start_date: str, timeout: float = 600.0, end_date: Optional[str] = None) -> list[Any]:
        # get_events_for_range (start_date, end_date=None)
        # https://github.com/bitwarden-labs/events-public-api-client/blob/main/main.py
        params = {"start": start_date}
        if end_date:
            params["end"] = end_date

        self.__logger.info(f"Fetching events for time range: {start_date} to {end_date or 'now'}")
        all_events = []
        continuation_token = None
        page = 1
        base_url = f"{API_URL}/events"
        timeout_start = time.time()

        while time.time() < timeout_start + timeout:
            if continuation_token:
                params["continuationToken"] = continuation_token
            self.__logger.debug(f"Fetching page {page} of events...")
            response = session.get(
                base_url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:  # Too Many Requests
                retry_after = int(response.headers.get("Retry-After", 60))
                self.__logger.warning(f"Rate limit hit. Waiting {retry_after} seconds before retrying...")
                time.sleep(retry_after)
                continue

            try:
                response.raise_for_status()
            except HTTPError as error:
                raise Exception("Failed to retrieve events report", response.content, error) from error

            data = response.json()
            events = data.get("data", [])
            all_events.extend(events)
            self.__logger.info(f"Retrieved {len(events)} events from page {page}")

            continuation_token = data.get("continuationToken")
            if not continuation_token:
                break
            page += 1

        self.__logger.info(
            f"Successfully fetched {len(all_events)} events for time range: {start_date} to {end_date or 'now'}"
        )
        return all_events

    def __fetch_token(self) -> str:
        if self.bitwarden_access_token is None:
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
            self.bitwarden_access_token = response_json["access_token"]
        session.headers.update({"Authorization": f"Bearer {self.bitwarden_access_token}"})
        return self.bitwarden_access_token

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
        return str(self.__get_collection(collection_id).get("externalId", ""))

    def __list_collections(self) -> List[Dict[str, Any]]:
        response = session.get(f"{API_URL}/collections")
        try:
            response.raise_for_status()
            response_json: Dict[str, Any] = response.json()
            return list(response_json.get("data", []))
        except HTTPError as error:
            raise Exception("Failed to list collections", response.content, error) from error

    def get_pending_users(self) -> List[Dict[str, Any]]:
        self.__fetch_token()
        pending = []
        for user in self.get_users():
            if user.get("status") == UserStatus.INVITED:
                pending.append(user)
        return pending

    def invite_user(self, user: UmpUser) -> str:
        self.__fetch_token()
        response = session.post(
            f"{API_URL}/members",
            json={
                "type": UserType.REGULAR_USER,
                "accessAll": False,
                "resetPasswordEnrolled": True,
                "externalId": user.username,
                "email": user.email,
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
                return self.fetch_user_id_by_external_id(user.username)
            raise Exception("Failed to invite user", response.content, error) from error

        self.__logger.info("User has been invited to Bitwarden")
        response_json: Dict[str, str] = response.json()
        return response_json.get("id", "")

    def reinvite_user(self, id: str, username: str) -> None:
        response = session.post(f"{API_URL}/members/{id}/reinvite", timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response.raise_for_status()
            self.__logger.info(f"{username} has been reinvited to Bitwarden")
        except HTTPError as error:
            raise Exception(f"Failed to reinvite {username}", response.content, error) from error

    def grant_can_manage_permission_to_team_collections(self, user: UmpUser, teams: List[str]) -> None:
        collections = self.list_existing_collections(teams=teams)
        assign_collections = []
        _can_manage_collections = []
        for key, value in collections.items():
            if value["id"] == "duplicate":
                raise Exception(f"Duplicate collection found - {key}")
            if user.can_manage_team_collection(team=key):
                assign_collections.append(
                    {
                        "id": value["id"],
                        "readOnly": False,
                        "hidePasswords": False,
                        "manage": True,
                    }
                )
                _can_manage_collections.append(key)

        if len(assign_collections) == 0:
            return

        bw_user = self.get_user_by_email(email=str(user.email))
        bw_user_collections = self.__get_user_collections(bw_user.get("collections", []))
        for bw_user_collection in bw_user_collections:
            if self.__collection_manually_created(bw_user_collection["id"]):
                assign_collections.append(
                    next(item for item in bw_user.get("collections", []) if item["id"] == bw_user_collection["id"])
                )

        response = session.put(
            f"{API_URL}/members/{bw_user['id']}",
            json={
                "type": bw_user["type"],
                "externalId": bw_user["externalId"],
                "resetPasswordEnrolled": bw_user["resetPasswordEnrolled"],
                "permissions": bw_user["permissions"],
                "collections": assign_collections,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception('Failed to grant "can manage" permission to user', response.content, error) from error

        self.__logger.info(f'User has been granted "can manage" permissions to collections: {_can_manage_collections}')

    def assign_custom_permissions_to_platsec_user(self, user: UmpUser, teams: List[str]) -> None:
        bw_user = self.get_user_by_email(email=str(user.email))
        permissions = {
            "accessEventLogs": True,
            "accessImportExport": False,
            "accessReports": True,
            "createNewCollections": False,
            "editAnyCollection": False,
            "deleteAnyCollection": False,
            "manageGroups": False,
            "managePolicies": False,
            "manageSso": False,
            "manageUsers": True,
            "manageResetPassword": True,
            "manageScim": False,
        }
        if user.is_a_support_admin(teams, bw_user["type"]):
            response = session.put(
                f"{API_URL}/members/{bw_user['id']}",
                json={
                    "type": 4,
                    "permissions": permissions,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            try:
                response.raise_for_status()
            except HTTPError as error:
                raise Exception(
                    "Failed to grant custom permissions to PlatSec user", response.content, error
                ) from error

        self.__logger.info(f"PlatSec user {user.username} has been granted custom permissions")

    def remove_user(self, username: str) -> None:
        self.__fetch_token()
        try:
            uid = self.fetch_user_id_by_external_id(external_id=username)
        except Exception:
            self.__logger.info(f"User {username} not found in the Bitwarden organisation")
            return

        self.remove_user_by_id(
            user_id=uid,
            username=username,
        )
        self.__logger.info(f"User {username} has been removed from the Bitwarden organisation")

    @staticmethod
    def remove_user_by_id(user_id: str, username: str) -> None:
        response = session.delete(
            f"{API_URL}/members/{user_id}",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise BitwardenAPIException(f"Failed to delete user {username}", response.content, error) from error

    def get_groups(self) -> Dict[str, str]:
        response = session.get(f"{API_URL}/groups", timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get groups") from error
        response_json: Dict[str, Any] = response.json()
        return {group.get("name"): group.get("id") for group in response_json.get("data", [])}

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
        return str(response_json.get("id", ""))

    def _user_custom_group_ids(self, existing_user_group_ids: List[str], custom_group_ids: List[str]) -> List[str]:
        return [id for id in existing_user_group_ids if id in custom_group_ids]

    def associate_user_to_groups(self, user_id: str, managed_group_ids: List[str], custom_group_ids: List[str]) -> None:
        existing_user_group_ids = self.__get_user_groups(user_id)

        user_group_ids = managed_group_ids + self._user_custom_group_ids(existing_user_group_ids, custom_group_ids)

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

    def list_existing_collections(self, teams: List[str]) -> Dict[str, Dict[str, Any]]:
        collections: Dict[str, Dict[str, Any]] = {}
        for collection_object in self.__list_collections():
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
        self, teams: List[str], groups: Dict[str, str], collections: Dict[str, Dict[str, Any]]
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

    def get_users_by_group_name(self, group_name: str) -> List[str]:
        # get the group_id for our name
        group_id = self.get_group_id_by_name(group_name)
        if not group_id:
            self.__logger.info(f"Group {group_name} not found")
            return []
        users = self.get_users_in_group(group_id)

        return users

    @staticmethod
    def get_group_id_by_name(group_name: str) -> str:
        response = session.get(f"{API_URL}/groups/")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to retrieve groups", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        groups = list(response_json.get("data", []))
        for group in groups:
            if group.get("name", "") == group_name:
                return str(group.get("id", ""))
        return ""

    def get_users_in_group(self, group_id: str) -> List[str]:
        # this endpoint just returns a list of user ids
        if not group_id:
            self.__logger.warning("group_id cannot be empty")
            return []
        response = session.get(f"{API_URL}/groups/{group_id}/member-ids")
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get users in group", response.content, error) from error
        users: List[str] = response.json()
        return users
