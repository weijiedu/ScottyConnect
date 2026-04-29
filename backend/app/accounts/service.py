"""
Account Service
Handles registration, verification, and login using UserDAO for persistence.
"""

import os

from dotenv import load_dotenv

from app.accounts.model.User import User
from app.accounts.schemas import (
    LoginRequest,
    RegisterRequest,
    VerifyRequest,
    PublicUser,
    RegisterResponse,
    VerifyResponse,
    LoginResponse,
    UpdateProfileRequest,
)
from app.accounts.user_dao import UserDAO
from app.logging.service import LoggerService
from app.utils.jwt import JWT
from app.utils.bcrypt import hash_password, verify_password
from app.bus.message_bus import Service
from app.bus.message import Message, MessageType
from app.utils.verification import generate_verification_code

load_dotenv()

ACCOUNT_SERVICE_EXTENSION_KEY = "account_service"


def get_account_service() -> "AccountService":
    from flask import current_app

    return current_app.extensions[ACCOUNT_SERVICE_EXTENSION_KEY]


"""
Account Service extends the Service base class from the message bus, utilize the message bus to publish and subscribe to messages.
"""
class AccountService(Service):
    def __init__(self, user_dao: UserDAO | None = None) -> None:
        super().__init__()
        self.key = ACCOUNT_SERVICE_EXTENSION_KEY
        self._users = user_dao or UserDAO()
        self._logger = LoggerService(service_name=self.key)
        secret = os.getenv("JWT_SECRET")
        if not secret:
            raise ValueError("JWT_SECRET is not set")
        self._tokens = JWT(secret_key=secret)

    @staticmethod
    def _to_public_user(user: User) -> PublicUser:
        return PublicUser(
            id=user.id,
            username=user.username,
            email=user.email,
            verified=user.verified,
            role=user.role,
            bio=user.bio,
            tags=user.tags,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def register(self, request: RegisterRequest) -> RegisterResponse:
        # Check if passwords match
        if request.password != request.confirm_password:
            return RegisterResponse(message="Passwords do not match", user=None, code=400)

        # Check if email ends in cmu.edu
        if not request.email.endswith("cmu.edu"):
            return RegisterResponse(message="Must be a CMU affiliated email (@xxx.cmu.edu)", user=None, code=400)

        # Verification number
        verification_code = generate_verification_code()

        # Create user
        user = User(
            username=request.username,
            email=request.email,
            password=hash_password(request.password),
            verification_code=hash_password(verification_code),
            role=request.role,
        )
        
        # Insert user
        try:
            saved = self._users.insert(user)
        # Return error if user already exists
        except ValueError as e:
            return RegisterResponse(message=str(e), user=None, code=400)
        
        # Publish message
        self.publishMessage(Message(MessageType.REGISTER_MESSAGE, 
            {
                "username": saved.username,
                "recipient_email": saved.email,
                "verification_code": verification_code,
            }
        ))
        self._logger.info(f"User {saved.username} registered successfully", user_id=saved.id)
        return RegisterResponse(message="Success", user=self._to_public_user(saved), code=201)

    def verify(self, request: VerifyRequest) -> VerifyResponse:
        # Find user by email
        user = self._users.find_by_email(request.email)
        
        # Check if user exists
        if user is None:
            return VerifyResponse(message="User not found", user=None, token=None, code=404)
        
        # Check if verification code is correct
        if not verify_password(request.code, user.verification_code):
            return VerifyResponse(message="Invalid verification code", user=None, token=None, code=401)
        
        # Set user as verified
        self._users.set_verified(request.email, True)
        
        # Generate token
        token = self._tokens.generate_token(user.id)

        # Return response
        verified_user = user.model_copy(update={"verified": True})
        self._logger.info(f"User {verified_user.username} verified successfully", user_id=verified_user.id)
        return VerifyResponse(
            message="Success",
            user=self._to_public_user(verified_user),
            token=token,
            code=200,
        )

    def login(self, request: LoginRequest) -> LoginResponse:
        # Find user by username
        user = self._users.find_by_username(request.username)
        
        # Check if user exists
        if user is None:
            return LoginResponse(message="Invalid credentials", user=None, token=None, code=401)
        
        # Check if password is correct
        if not verify_password(request.password, user.password):
            return LoginResponse(message="Invalid credentials", user=None, token=None, code=401)
        
        # Check if user is verified (return user so client can route to verify with email)
        if not user.verified:
            return LoginResponse(
                message="Account not verified",
                user=self._to_public_user(user),
                token=None,
                code=403,
            )
        
        # Generate token
        token = self._tokens.generate_token(user.id)
        self._logger.info(f"User {user.username} logged in.", user_id=user.id)
        # Return response
        return LoginResponse(
            message="Success",
            user=self._to_public_user(user),
            token=token,
            code=200,
        )
    
    def update_profile(self, request: UpdateProfileRequest) -> bool:
        """Updates the bio and tags for a user."""
        user = self._users.find_by_id(request.user_id)
        if not user:
            return False
        
        user.bio = request.bio
        user.tags = request.tags
        self._logger.info(f"User {user.username} updated profile", user_id=user.id)
        return self._users.update(user)

    def get_discover_users(self, current_user_id: str | None = None) -> list[PublicUser]:
        """Returns a list of all users, potentially excluding the current user."""
        # For now, just return all users from the collection
        cursor = self._users._col.find()
        users = []
        for doc in cursor:
            user = self._users._to_user(doc)
            if user and user.id != current_user_id:
                users.append(self._to_public_user(user))
        return users
