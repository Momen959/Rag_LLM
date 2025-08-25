from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from src.models.user_model import (
    UserCreate, 
    UserLogin, 
    UserResponse, 
    TokenResponse,
    PasswordChangeRequest
)
from src.service.authentication_service import (
    auth_service, 
    get_current_user_bearer
)
from src.service.user_service import user_service
from src.exceptions.exceptions import (
    UserRepositoryError,
    UserExistsError,
    UserNotFoundError,
    UserUpdateError,
    UserDeleteError
)

auth_router = APIRouter(prefix='/auth', tags=["authentication"])


@auth_router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user"""
    try:
        return await auth_service.register(
            email=user.email, 
            password=user.password.get_secret_value()
        )
    except UserExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except UserRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@auth_router.post("/login", response_model=TokenResponse)
async def login(user: UserLogin):
    """Login and get access token"""
    try:
        return await auth_service.login(
            email=user.email, 
            password=user.password.get_secret_value()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@auth_router.get("/me", response_model=UserResponse)
async def me(current_user: Dict[str, Any] = Depends(get_current_user_bearer)):
    """Get the current user's profile"""
    try:
        user = await user_service.get_user_by_id(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except UserRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user profile: {str(e)}"
        )


@auth_router.post("/change-password", response_model=UserResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Change the current user's password"""
    try:
        return await user_service.change_password(
            user_id=current_user["user_id"],
            current_password=password_data.current_password.get_secret_value(),
            new_password=password_data.new_password.get_secret_value()
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except UserUpdateError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )
    except UserRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@auth_router.post("/logout")
async def logout():
    """
    Logout endpoint.
    
    For stateless JWT tokens, logout is handled client-side by removing the token.
    This endpoint exists mainly for API consistency and to support future server-side
    logout functionality if needed (token blacklisting, etc.).
    """
    return {"message": "Logged out successfully"}


@auth_router.delete("/account", response_model=Dict[str, str])
async def delete_account(
    current_user: Dict[str, Any] = Depends(get_current_user_bearer)
):
    """Delete the current user's account"""
    try:
        await user_service.delete_user(current_user["user_id"])
        return {"message": "Account deleted successfully"}
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except UserDeleteError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
    except UserRepositoryError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )