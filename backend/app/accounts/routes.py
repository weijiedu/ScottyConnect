# backend/app/accounts/routes.py
"""
Routes for the accounts service.
"""
from flask import Blueprint, jsonify

from app.accounts.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    VerifyRequest,
    VerifyResponse,
    UpdateProfileRequest,
)
from app.accounts.service import get_account_service
from app.utils.doc import doc
from app.utils.validate import validate

accounts = Blueprint("accounts", __name__)


# Decorator order convention: @route -> @validate -> @doc
@accounts.route("/register", methods=["POST"])
@validate(RegisterRequest)
@doc(
    request=RegisterRequest,
    response=RegisterResponse,
    description="Register a new user account",
    tags=["accounts"],
    success_status=201,
)
def register(req: RegisterRequest):
    response = get_account_service().register(req)
    return jsonify(response.model_dump(mode="json")), response.code


@accounts.route("/verify", methods=["POST"])
@validate(VerifyRequest)
@doc(
    request=VerifyRequest,
    response=VerifyResponse,
    description="Verify a user account with email code",
    tags=["accounts"],
    success_status=200,
)
def verify(req: VerifyRequest):
    resp = get_account_service().verify(req)
    return jsonify(resp.model_dump(mode="json")), resp.code


@accounts.route("/login", methods=["POST"])
@validate(LoginRequest)
@doc(
    request=LoginRequest,
    response=LoginResponse,
    description="Authenticate a user account",
    tags=["accounts"],
    success_status=200,
)
def login(req: LoginRequest):
    resp = get_account_service().login(req)
    return jsonify(resp.model_dump(mode="json")), resp.code


@accounts.route("/profile", methods=["PUT"])
@validate(UpdateProfileRequest)
@doc(
    request=UpdateProfileRequest,
    description="Update user profile (bio and tags)",
    tags=["accounts"],
    success_status=200,
)
def update_profile(req: UpdateProfileRequest):
    success = get_account_service().update_profile(req)
    if success:
        return jsonify({"message": "Profile updated successfully"}), 200
    return jsonify({"message": "Failed to update profile"}), 400


@accounts.route("/discover", methods=["GET"])
@doc(
    description="Discover other users for networking",
    tags=["accounts"],
    success_status=200,
)
def discover():
    # In a real app, we'd get current_user_id from JWT
    users = get_account_service().get_discover_users()
    data = [u.model_dump(mode="json") for u in users]
    return jsonify({"users": data}), 200
