import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config.settings import get_settings
from src.models.user_model import UserResponse, TokenResponse
from src.service.user_service import user_service
from src.exceptions.exceptions import (
    UserRepositoryError, 
    UserNotFoundError,
    UserExistsError,
    TokenError,
    TokenExpiredError,
    InvalidCredentialsError
)

settings = get_settings()
security = HTTPBearer()


class AuthenticationService:
    """
    Service for handling authentication-related operations.
    
    This service handles JWT token creation, validation, and user authentication.
    It delegates user management operations to the UserService.
    """
    
    def __init__(self):
        if not settings.JWT_SECRET:
            raise RuntimeError("JWT secret is not configured. Set JWT_SECRET in settings.")

    def create_access_token(self, *, user_id: str, email: str) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user_id: User's MongoDB ID as string
            email: User's email address
            
        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        try:
            return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        except Exception as e:
            raise TokenError(f"Failed to create access token: {str(e)}")

    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT access token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            TokenExpiredError: If token is expired
            TokenError: If token is invalid
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token expired")
        except jwt.InvalidTokenError:
            raise TokenError("Invalid token")

    async def get_current_user(self, request: Request) -> Dict[str, Any]:
        """
        Extract and validate the current user from a request.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Dictionary with user_id and email
            
        Raises:
            TokenError: If the token is missing or invalid
            UserNotFoundError: If the user doesn't exist
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise TokenError("Missing Bearer token")
        
        token = auth_header.split(" ", 1)[1].strip()
        payload = self.decode_access_token(token)
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise TokenError("Invalid token payload")
        
        # Verify user exists in database
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        return {"user_id": user_id, "email": email}

    async def register(self, email: str, password: str) -> UserResponse:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            UserResponse with created user data
            
        Raises:
            UserExistsError: If a user with the email already exists
            UserRepositoryError: If there's a database error
        """
        return await user_service.create_user(email, password)

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and issue a JWT token.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            TokenResponse with access token
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            UserRepositoryError: If there's a database error
        """
        user = await user_service.get_user_by_email(email)
        if not user or not user_service.verify_password(password, user["password"]):
            raise InvalidCredentialsError("Invalid credentials")
        
        # Update last login time
        try:
            await user_service.update_last_login(user["_id"])
        except (UserNotFoundError, UserRepositoryError):
            # Non-critical error, continue with login
            pass
        
        try:
            token = self.create_access_token(user_id=user["_id"], email=user["email"])
            return TokenResponse(access_token=token, token_type="bearer")
        except TokenError:
            raise


# Global service instance
auth_service = AuthenticationService()


# Dependency for FastAPI routes using HTTPBearer (better for Swagger UI)
async def get_current_user_bearer(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user using HTTPBearer.
    
    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI security dependency
        
    Returns:
        Dictionary with user_id and email
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        payload = auth_service.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise TokenError("Invalid token payload")

        # Verify user exists in database
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")

        return {"user_id": user_id, "email": email}
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Authentication error: {str(e)}"
        )


# Alternative dependency using manual header parsing
async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    FastAPI dependency to get the current authenticated user using manual header parsing.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Dictionary with user_id and email
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await auth_service.get_current_user(request)
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Authentication error: {str(e)}"
        )