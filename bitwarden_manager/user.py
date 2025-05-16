from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, Optional, Any


# Bitwarden server enum definition:
# https://github.com/bitwarden/server/blob/main/src/Core/AdminConsole/Enums/OrganizationUserType.cs
class UserType(IntEnum):
    OWNER = 0
    ADMIN = 1
    REGULAR_USER = 2
    CUSTOM = 4
    # MANAGER is no longer supported but still in bitwarden server code
    # https://github.com/bitwarden/server/blob/main/src/Core/AdminConsole/Enums/OrganizationUserType.cs#L8
    MANAGER = 3  # So left here for completeness


# https://github.com/bitwarden/server/blob/main/src/Core/AdminConsole/Enums/OrganizationUserStatusType.cs
class UserStatus(IntEnum):
    INVITED = 0
    ACCEPTED = 1
    CONFIRMED = 2
    REVOKED = -1


ump_role_to_collection_permission_mapping = {
    "user": {"can_manage_team_collection": False},
    "super_admin": {"can_manage_team_collection": False},
    "team_admin": {"can_manage_team_collection": True},
    "all_team_admin": {"can_manage_team_collection": True},
}


@dataclass
class UmpUser:
    username: str
    roles_by_team: Dict[str, str]
    email: Optional[str] = None

    def can_manage_team_collection(self, team: str) -> bool:
        role = self.roles_by_team.get(team, "user")
        return bool(ump_role_to_collection_permission_mapping[role]["can_manage_team_collection"])

    def is_a_support_admin(self, teams: list[str], bw_user_type: int) -> bool:
        return "Platform Security" in teams and bw_user_type == UserType.REGULAR_USER


class BitwardenUserResponse:
    def __init__(self, user: Dict[str, Any]):
        self.user = user

    def user_response(self) -> Dict[str, Any]:
        return {
            "email": self.user["email"],
            "twoFactorEnabled": self.user["twoFactorEnabled"],
            "status": UserStatus(self.user["status"]).name,
            "type": UserType(self.user["type"]).name,
            "collections": self.user["collections"],
            "externalId": self.user["externalId"],
            "permissions": self.user["permissions"],
        }
