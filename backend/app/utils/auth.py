"""
Lightweight authentication decorator using the existing JWT utility.
Extracts user_id from the Authorization header and passes it to the view.
"""
import os
from functools import wraps

from flask import jsonify, request, g

from app.utils.jwt import JWT

_jwt: JWT | None = None


def _get_jwt() -> JWT:
    global _jwt
    if _jwt is None:
        secret = os.getenv("JWT_SECRET")
        if not secret:
            raise ValueError("JWT_SECRET is not set")
        _jwt = JWT(secret_key=secret)
    return _jwt


def try_get_request_user_id() -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    token = header[len("Bearer ") :]
    try:
        payload = _get_jwt().verify_token(token)
    except Exception:
        return None

    return payload.get("user_id")


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"message": "Missing or invalid Authorization header"}), 401

        token = header[len("Bearer "):]
        try:
            payload = _get_jwt().verify_token(token)
        except Exception as e:
            return jsonify({"message": str(e)}), 401

        g.user_id = payload["user_id"]
        return view(*args, **kwargs)

    return wrapped
