"""
User service — business logic for user-related operations.
"""
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.exceptions import UserNotFoundException


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int) -> User:
        """
        Get a user by their ID.
        
        Args:
            user_id: The user's database ID.
        
        Returns:
            The User object.
        
        Raises:
            UserNotFoundException: If user does not exist.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user

    def get_user_by_email(self, email: str) -> User | None:
        """
        Get a user by their email address.
        
        Args:
            email: The user's email.
        
        Returns:
            The User object or None.
        """
        return self.db.query(User).filter(User.email == email).first()
