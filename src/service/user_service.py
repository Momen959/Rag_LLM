import bcrypt
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.config.settings import get_settings
from src.repository.user_repository import UserRepository
from src.exceptions.exceptions import (
    UserRepositoryError,
    UserExistsError,
    UserNotFoundError,
    UserUpdateError,
    UserDeleteError
)
from src.models.user_model import UserResponse, UserDetail

settings = get_settings()


class UserService:
    """
    Service for handling user-related operations.
    
    This service contains business logic for user operations and delegates
    database operations to the UserRepository.
    """
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plain password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")
    
    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        """Verify a plain password against a hash"""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False
    
    async def create_user(self, email: str, password: str, additional_data: Dict[str, Any] = None) -> UserResponse:
        """
        Create a new user.
        
        Args:
            email: User's email address
            password: Plain password to be hashed
            additional_data: Optional additional user data
            
        Returns:
            UserResponse with created user data
            
        Raises:
            UserExistsError: If a user with the same email already exists
            UserRepositoryError: If there's an error during database operations
        """
        # Hash the password
        password_hash = self.hash_password(password)
        
        # Prepare user data
        user_data = {
            "email": email,
            "password": password_hash,
            "created_at": settings.get_utc_now()
        }
        
        # Add any additional data
        if additional_data:
            user_data.update(additional_data)
        
        # Create the user in the repository
        user = await self.user_repo.create_user(user_data)
        
        # Return user response
        return UserResponse(
            id=user["_id"],
            email=user["email"],
            created_at=user.get("created_at")
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserDetail]:
        """
        Get a user by their ID.
        
        Args:
            user_id: User's MongoDB ID as string
            
        Returns:
            UserDetail or None if not found
            
        Raises:
            UserRepositoryError: If there's an error during database operations
        """
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            return None
        
        return UserDetail(
            id=user["_id"],
            email=user["email"],
            created_at=user.get("created_at"),
            updated_at=user.get("updated_at"),
            is_active=user.get("is_active", True),
            roles=user.get("roles", []),
            last_login=user.get("last_login")
        )
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by their email address.
        
        Args:
            email: User's email address
            
        Returns:
            User document or None if not found
            
        Raises:
            UserRepositoryError: If there's an error during database operations
        """
        return await self.user_repo.find_by_email(email)
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> UserResponse:
        """
        Update a user's information.
        
        Args:
            user_id: User's MongoDB ID as string
            update_data: Dictionary of fields to update
            
        Returns:
            Updated UserResponse
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            UserUpdateError: If there's an error during the update
            UserRepositoryError: If there's an error during database operations
        """
        # If password is in update data, hash it
        if "password" in update_data:
            update_data["password"] = self.hash_password(update_data["password"])
        
        # Update the user
        updated_user = await self.user_repo.update_user(user_id, update_data)
        
        # Return updated user response
        return UserResponse(
            id=updated_user["_id"],
            email=updated_user["email"],
            created_at=updated_user.get("created_at"),
            updated_at=updated_user.get("updated_at")
        )
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> UserResponse:
        """
        Change a user's password.
        
        Args:
            user_id: User's MongoDB ID as string
            current_password: User's current password for verification
            new_password: New password to set
            
        Returns:
            Updated UserResponse
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            ValueError: If the current password is incorrect
            UserUpdateError: If there's an error during the update
            UserRepositoryError: If there's an error during database operations
        """
        # Get the user
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        
        # Verify current password
        if not self.verify_password(current_password, user["password"]):
            raise ValueError("Current password is incorrect")
        
        # Hash the new password
        new_password_hash = self.hash_password(new_password)
        
        # Update the password
        updated_user = await self.user_repo.update_password(user_id, new_password_hash)
        
        # Return updated user
        return UserResponse(
            id=updated_user["_id"],
            email=updated_user["email"],
            created_at=updated_user.get("created_at"),
            updated_at=updated_user.get("updated_at")
        )
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user account.
        
        Args:
            user_id: User's MongoDB ID as string
            
        Returns:
            True if deletion was successful
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            UserDeleteError: If there's an error during deletion
            UserRepositoryError: If there's an error during database operations
        """
        return await self.user_repo.delete_user(user_id)
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        List users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of UserResponse objects
            
        Raises:
            UserRepositoryError: If there's an error during database operations
        """
        users = await self.user_repo.list_users(skip, limit)
        return [
            UserResponse(
                id=user["_id"],
                email=user["email"],
                created_at=user.get("created_at"),
                updated_at=user.get("updated_at")
            )
            for user in users
        ]
    
    async def count_users(self) -> int:
        """
        Count the total number of users.
        
        Returns:
            Total number of users
            
        Raises:
            UserRepositoryError: If there's an error during database operations
        """
        return await self.user_repo.count_users()
    
    async def update_last_login(self, user_id: str) -> None:
        """
        Update a user's last login timestamp.
        
        Args:
            user_id: User's MongoDB ID as string
            
        Raises:
            UserUpdateError: If there's an error during the update
            UserRepositoryError: If there's an error during database operations
        """
        await self.user_repo.update_user(
            user_id, 
            {"last_login": settings.get_utc_now()}
        )
    
    async def search_users(self, criteria: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        Search users based on criteria.
        
        Args:
            criteria: Search criteria as field-value pairs
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching UserResponse objects
            
        Raises:
            UserRepositoryError: If there's an error during database operations
        """
        users = await self.user_repo.find_users_by_criteria(criteria, skip, limit)
        return [
            UserResponse(
                id=user["_id"],
                email=user["email"],
                created_at=user.get("created_at"),
                updated_at=user.get("updated_at")
            )
            for user in users
        ]


# Global service instance
user_service = UserService()