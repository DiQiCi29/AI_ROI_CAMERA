from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.fcm_token import FCMToken
from app.schemas.auth import LoginRequest, FCMTokenRequest, LogoutRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail={
            "code": "UNAUTHORIZED", "message": "Sai tên đăng nhập hoặc mật khẩu"
        })
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"success": True, "data": {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 86400
    }}

@router.post("/register-fcm-token")
def register_fcm(
    body: FCMTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(FCMToken).filter(FCMToken.token == body.fcm_token).first()
    if not existing:
        fcm = FCMToken(user_id=current_user.id, token=body.fcm_token,
                       device_name=body.device_id, is_active=True)
        db.add(fcm)
        db.commit()
    return {"success": True, "message": "FCM token registered successfully"}

@router.delete("/logout")
def logout(
    body: LogoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(FCMToken).filter(
        FCMToken.user_id == current_user.id,
        FCMToken.device_name == body.device_id
    ).delete()
    db.commit()
    return {"success": True, "message": "Logged out successfully"}