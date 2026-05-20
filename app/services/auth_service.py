"""
Authentication Service
Contains business logic for user authentication and account management
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.user import User, UserRole
from app.models.fcm_token import FCMToken
from app.core.security import hash_password, verify_password


class AuthService:
    """Service for handling authentication operations"""

    @staticmethod
    def authenticate_user(username: str, password: str, db: Session) -> User | None:
        """
        Authenticate user by username and password
        
        Args:
            username: User's username
            password: User's plain password
            db: Database session
            
        Returns:
            User object if authentication successful, None otherwise
        """
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_user(username: str, email: str, password: str, 
                   role: UserRole = UserRole.viewer, db: Session = None) -> User:
        """
        Create a new user account
        
        Args:
            username: Desired username
            email: User's email
            password: Plain password (will be hashed)
            role: User role (admin or viewer)
            db: Database session
            
        Returns:
            Created User object
        """
        hashed_pwd = hash_password(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_pwd,
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str, 
                       db: Session) -> bool:
        """
        Change user password
        
        Args:
            user: User object
            old_password: Current password (plain)
            new_password: New password (plain)
            db: Database session
            
        Returns:
            True if successful, False if old password incorrect
        """
        if not verify_password(old_password, user.hashed_password):
            return False
        
        user.hashed_password = hash_password(new_password)
        db.commit()
        return True

    @staticmethod
    def register_fcm_token(user_id: int, fcm_token: str, device_name: str, 
                          db: Session) -> FCMToken:
        """
        Register or update FCM token for a device
        
        Args:
            user_id: User ID
            fcm_token: Firebase token
            device_name: Device identifier
            db: Database session
            
        Returns:
            FCMToken object
        """
        existing = db.query(FCMToken).filter(FCMToken.token == fcm_token).first()
        
        if existing:
            existing.is_active = True
            existing.last_used_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        
        fcm = FCMToken(
            user_id=user_id,
            token=fcm_token,
            device_name=device_name,
            is_active=True,
            last_used_at=datetime.utcnow()
        )
        db.add(fcm)
        db.commit()
        db.refresh(fcm)
        return fcm

    @staticmethod
    def unregister_fcm_token(user_id: int, device_name: str, db: Session) -> int:
        """
        Unregister FCM token (logout device)
        
        Args:
            user_id: User ID
            device_name: Device identifier
            db: Database session
            
        Returns:
            Number of tokens deleted
        """
        result = db.query(FCMToken).filter(
            FCMToken.user_id == user_id,
            FCMToken.device_name == device_name
        ).delete()
        db.commit()
        return result

    @staticmethod
    def get_user_devices(user_id: int, db: Session) -> list:
        """
        Get all registered devices for a user
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of FCMToken objects
        """
        return db.query(FCMToken).filter(
            FCMToken.user_id == user_id,
            FCMToken.is_active == True
        ).all()

    @staticmethod
    def deactivate_user(user_id: int, db: Session) -> bool:
        """
        Deactivate user account
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            True if successful
        """
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False
            db.commit()
            return True
        return False
