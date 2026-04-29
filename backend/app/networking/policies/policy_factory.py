from __future__ import annotations

from app.networking.policies.invite_policy import (
    AlumniInvitePolicy,
    InvitePolicy,
    StudentInvitePolicy,
)


# Resolves invite policy by sender role.
class InvitePolicyFactory:

    def __init__(self) -> None:
        self._role_to_policy: dict[str, InvitePolicy] = {
            "STUDENT": StudentInvitePolicy(),
            "ALUMNI": AlumniInvitePolicy(),
        }

    def for_role(self, role: str) -> InvitePolicy:
        policy = self._role_to_policy.get(role.upper())
        if policy is None:
            raise ValueError(f"Invalid role: {role}. Supported roles: {list(self._role_to_policy.keys())}")
        return policy
