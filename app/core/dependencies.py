from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid token"})
    except JWTError:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED", "message": "Token expired or invalid"})

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "User not found"})
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user has admin role"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin role required"}
        )
    return current_user

def require_viewer(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user has viewer role"""
    if current_user.role not in [UserRole.viewer, UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Viewer or admin role required"}
        )
    return current_user