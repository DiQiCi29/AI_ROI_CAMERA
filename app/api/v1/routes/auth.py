from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, hash_password, decode_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.fcm_token import FCMToken
from app.models.token_blacklist import TokenBlacklist
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
    authorization: str = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Xóa FCM token của thiết bị này
    db.query(FCMToken).filter(
        FCMToken.user_id == current_user.id,
        FCMToken.device_name == body.device_id
    ).delete()
    
    # Blacklist JWT token hiện tại — logout tức thì
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                blacklisted = TokenBlacklist(token_jti=jti)
                db.add(blacklisted)
        except Exception:
            pass  # Nếu decode lỗi thì vẫn xóa FCM token
    
    db.commit()
    return {"success": True, "message": "Logged out successfully"}

