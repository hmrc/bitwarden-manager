# To be removed once run in production

import logging
from typing import Any, Dict, List
from requests import HTTPError, get
from bitwarden_manager.clients.bitwarden_public_api import session, UserType, BitwardenPublicApi
from bitwarden_manager.clients.user_management_api import UserManagementApi

UMP_API_URL = "https://user-management-backend-production.tools.tax.service.gov.uk/v2"
BITWARDEN_API_URL = "https://api.bitwarden.com/public"
REQUEST_TIMEOUT_SECONDS = 10


def get_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    return logger


logger = get_logger()


class UmpApi:
    def __init__(self, user_management_api: UserManagementApi) -> None:
        self.user_management_api = user_management_api

    def get_teams(self) -> List[str]:
        bearer = self.user_management_api._UserManagementApi__fetch_token()  # type: ignore
        response = get(
            f"{UMP_API_URL}/organisations/teams",
            headers={
                "Token": bearer,
                "requester": self.user_management_api._UserManagementApi__client_id,  # type: ignore
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        logger.info(response.json())
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise Exception("Failed to get teams", response.content, e) from e
        response_json: Dict[str, Any] = response.json()
        return [t.get("team") for t in response_json.get("teams", [])]

    def get_team_admin_users(self, teams: List[str]) -> List[str]:
        bearer = self.user_management_api._UserManagementApi__fetch_token()  # type: ignore
        team_admins = []

        for team_name in teams:
            response = get(
                f"{UMP_API_URL}/organisations/teams/{team_name}/members",
                headers={
                    "Token": bearer,
                    "requester": self.user_management_api._UserManagementApi__client_id,  # type: ignore
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            try:
                response.raise_for_status()
            except HTTPError as e:
                raise Exception("Failed to get team members", response.content, e) from e
            response_json: Dict[str, Any] = response.json()
            for m in response_json.get("members", []):
                if m.get("role") == "team_admin":
                    team_admins.append(m.get("username"))
        return team_admins


class BitwardenApi:
    def __init__(self, bitwarden_public_api: BitwardenPublicApi) -> None:
        self.bitwarden_public_api = bitwarden_public_api

    def get_members_to_update(self, team_admin_users: List[str]) -> List[Dict[str, Any]]:
        members = []
        response = session.get(f"{BITWARDEN_API_URL}/members", timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception("Failed to get members", response.content, error) from error
        response_json: Dict[str, Any] = response.json()
        for m in response_json.get("data", []):
            if m.get("type") == UserType.REGULAR_USER and m.get("externalId", "") in team_admin_users:
                members.append(m)
        return members

    def update_member_role(self, member: Dict[str, Any]) -> None:
        response = session.put(
            f"{BITWARDEN_API_URL}/members/{member.get('id')}",
            json={
                "type": UserType.MANAGER,
                "accessAll": member.get("accessAll"),
                "externalId": member.get("externalId"),
                "resetPasswordEnrolled": member.get("resetPasswordEnrolled"),
                "collections": member.get("collections"),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except HTTPError as error:
            raise Exception(f"Failed to update role of member: {member.get('name')}") from error


class MemberRoleUpdater:
    def __init__(self, user_management_api: UserManagementApi, bitwarden_public_api: BitwardenPublicApi):
        self.ump = UmpApi(user_management_api)
        self.bw = BitwardenApi(bitwarden_public_api)

    def run(self) -> None:
        logger.info("Running role updater")
        teams = self.ump.get_teams()
        logger.info("Fetched UMP teams")
        team_admin_users = self.ump.get_team_admin_users(teams)
        logger.info("Fetched UMP team admin users")
        self.bw.bitwarden_public_api._BitwardenPublicApi__fetch_token()  # type: ignore
        logger.info("Fetched Bitwarden API Token")
        members_to_update = self.bw.get_members_to_update(team_admin_users)
        logger.info("Fetched Bitwarden users to update")
        for m in members_to_update:
            logger.info(f"Updating: {m.get('name')}")
            self.bw.update_member_role(m)
            logger.info(f"Updated role of member: {m.get('name')}")
