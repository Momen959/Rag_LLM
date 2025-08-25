from typing import Dict, Any, List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from bson import ObjectId

from src.config.settings import get_settings
from src.exceptions.exceptions import (
    UserRepositoryError, 
    UserNotFoundError,
    UserExistsError,
    UserUpdateError,
    UserDeleteError
)

settings = get_settings()


class UserRepository:
    """
    Repository for handling MongoDB user operations.
    
    This class provides CRUD operations for the users collection in MongoDB.
    All database-specific operations are encapsulated here, and service layers
    should interact with the database only through this repository.
    """

    def __init__(self, 
                 mongo_url: str = settings.MONGO_URL,
                 db_name: str = settings.DATABASE_NAME,
                 collection_name: str = settings.USERS_COLLECTION):
        """
        Initializes the UserRepository with MongoDB connection details.
        """
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.collection: AsyncIOMotorCollection = self.db[collection_name]
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new user in the database.
        
        Args:
            user_data: Dictionary containing user data (email, password_hash, etc.)
            
        Returns:
            The created user document with MongoDB _id
            
        Raises:
            UserExistsError: If a user with the same email already exists
            UserRepositoryError: If there's an error during the operation
        """
        try:
            # Check if user with this email already exists
            existing_user = await self.find_by_email(user_data.get("email"))
            if existing_user:
                raise UserExistsError(f"User with email {user_data.get('email')} already exists")
            
            # Set created_at timestamp if not provided
            if "created_at" not in user_data:
                user_data["created_at"] = settings.get_utc_now()
                
            # Insert user document
            result = await self.collection.insert_one(user_data)
            
            # Return the full user document
            created_user = await self.collection.find_one({"_id": result.inserted_id})
            if created_user:
                created_user["_id"] = str(created_user["_id"])
                return created_user
            else:
                raise UserRepositoryError("User created but could not be retrieved")
                
        except UserExistsError:
            raise
        except Exception as e:
            raise UserRepositoryError(f"Failed to create user: {str(e)}")
    
    async def find_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their MongoDB ObjectId.
        
        Args:
            user_id: String representation of MongoDB ObjectId
            
        Returns:
            User document or None if not found
            
        Raises:
            UserRepositoryError: If there's an error during the operation
        """
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            raise UserRepositoryError(f"Failed to find user by ID: {str(e)}")
    
    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User document or None if not found
            
        Raises:
            UserRepositoryError: If there's an error during the operation
        """
        try:
            user = await self.collection.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            raise UserRepositoryError(f"Failed to find user by email: {str(e)}")
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a user's information.
        
        Args:
            user_id: String representation of MongoDB ObjectId
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated user document
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            UserUpdateError: If there's an error during the update
        """
        try:
            # Check if user exists
            user = await self.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(f"User with ID {user_id} not found")
            
            # Add updated_at timestamp
            update_data["updated_at"] = settings.get_utc_now()
            
            # Perform the update
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise UserUpdateError(f"Failed to update user {user_id}, no changes made")
            
            # Return the updated user
            updated_user = await self.find_by_id(user_id)
            if not updated_user:
                raise UserUpdateError(f"User {user_id} was updated but could not be retrieved")
            
            return updated_user
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserUpdateError(f"Failed to update user: {str(e)}")
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user from the database.
        
        Args:
            user_id: String representation of MongoDB ObjectId
            
        Returns:
            True if deletion was successful
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            UserDeleteError: If there's an error during deletion
        """
        try:
            # Check if user exists
            user = await self.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(f"User with ID {user_id} not found")
            
            # Delete the user
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            
            if result.deleted_count == 0:
                raise UserDeleteError(f"Failed to delete user {user_id}")
            
            return True
            
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserDeleteError(f"Failed to delete user: {str(e)}")
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of user documents
            
        Raises:
            UserRepositoryError: If there's an error during the operation
        """
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            users = []
            
            async for user in cursor:
                user["_id"] = str(user["_id"])
                users.append(user)
                
            return users
            
        except Exception as e:
            raise UserRepositoryError(f"Failed to list users: {str(e)}")
    
    async def count_users(self) -> int:
        """
        Count the total number of users.
        
        Returns:
            Total number of users
            
        Raises:
            UserRepositoryError: If there's an error during the operation
        """
        try:
            return await self.collection.count_documents({})
        except Exception as e:
            raise UserRepositoryError(f"Failed to count users: {str(e)}")
    
    async def find_users_by_criteria(self, criteria: Dict[str, Any], 
                                    skip: int = 0, 
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find users that match specific criteria.
        
        Args:
            criteria: Dictionary of field-value pairs to match
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching user documents
            
        Raises:
            UserRepositoryError: If there's an error during the operation
        """
        try:
            cursor = self.collection.find(criteria).skip(skip).limit(limit)
            users = []
            
            async for user in cursor:
                user["_id"] = str(user["_id"])
                users.append(user)
                
            return users
            
        except Exception as e:
            raise UserRepositoryError(f"Failed to find users by criteria: {str(e)}")
    
    async def update_password(self, user_id: str, password_hash: str) -> Dict[str, Any]:
        """
        Update a user's password.
        
        Args:
            user_id: String representation of MongoDB ObjectId
            password_hash: Hashed password to store
            
        Returns:
            Updated user document
            
        Raises:
            UserNotFoundError: If the user doesn't exist
            UserUpdateError: If there's an error during the update
        """
        try:
            return await self.update_user(user_id, {"password": password_hash})
        except UserNotFoundError:
            raise
        except Exception as e:
            raise UserUpdateError(f"Failed to update password: {str(e)}")