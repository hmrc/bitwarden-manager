from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


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


ump_role_to_org_user_type_mapping = {
    "user": {"org_user_type": UserType.REGULAR_USER, "can_manage_team_collection": False},
    "super_admin": {"org_user_type": UserType.REGULAR_USER, "can_manage_team_collection": False},
    "team_admin": {"org_user_type": UserType.REGULAR_USER, "can_manage_team_collection": True},
    "all_team_admin": {"org_user_type": UserType.REGULAR_USER, "can_manage_team_collection": True},
}


@dataclass
class UmpUser:
    username: str
    email: Optional[str] = None
    role: str = "user"

    def org_user_type(self) -> int:
        return ump_role_to_org_user_type_mapping[self.role]["org_user_type"]

    def can_manage_team_collection(self) -> bool:
        return bool(ump_role_to_org_user_type_mapping[self.role]["can_manage_team_collection"])
