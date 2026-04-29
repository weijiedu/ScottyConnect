import os

import jwt
from datetime import datetime, timedelta, timezone


# Token Manager for JWT
"""
This class is used to generate and verify JWT tokens.
"""


class JWT:

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    """
    Generate a JWT token for a user.
    """
    def generate_token(self, user_id: str | int) -> str:
        hours = int(os.getenv("JWT_EXPIRES_HOURS", "24"))
        payload = {
            "user_id": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=hours),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    """
    Verify a JWT token.
    """
    def verify_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")