import os
import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session
from app.models.fcm_token import FCMToken
from app.models.alert import Alert


class FCMService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return

        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-adminsdk.json")
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            cls._initialized = True
            print("[FCM] Firebase initialized successfully")
        except FileNotFoundError:
            print(f"[FCM] Firebase credentials not found at {cred_path}")
            print("[FCM] FCM service will be disabled")
        except Exception as e:
            print(f"[FCM] Firebase initialization failed: {str(e)}")

    @classmethod
    def send_to_all(cls, title: str, body: str, data: dict = None):
        """
        Gửi FCM notification tới tất cả token đã đăng ký.
        Không cần DB session, dùng token từ DB query riêng.
        """
        if not cls._initialized:
            print("[FCM] Service not initialized, skipping notification")
            return

        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            tokens_query = db.query(FCMToken).filter(FCMToken.is_active == True).all()
            token_list = [token.token for token in tokens_query]
            if not token_list:
                print("[FCM] No active FCM tokens found")
                return

            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="intrusion_alert_channel",
                        sound="alert_sound",
                        color="#FF0000",
                        icon="ic_launcher_foreground",
                    )
                ),
                tokens=token_list
            )

            response = messaging.send_multicast(message)
            print(f"[FCM] Sent to {response.success_count} devices, {response.failure_count} failed")
        except Exception as e:
            print(f"[FCM] Error in send_to_all: {str(e)}")
        finally:
            db.close()

    @classmethod
    async def send_intrusion_alert(cls, alert: Alert, zone_name: str, db: Session):
        if not cls._initialized:
            print("[FCM] Service not initialized, skipping notification")
            return None

        tokens_query = db.query(FCMToken).filter(FCMToken.is_active == True).all()
        token_list = [token.token for token in tokens_query]
        if not token_list:
            print("[FCM] No active FCM tokens found")
            return None

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="⚠️ Cảnh báo xâm nhập!",
                body=f"Phát hiện xâm nhập tại: {zone_name}"
            ),
            data={
                "type": "intrusion_alert",
                "alert_id": str(alert.id),
                "zone_id": str(alert.zone_id) if alert.zone_id else "",
                "zone_name": zone_name,
                "detected_at": alert.detected_at.isoformat() if alert.detected_at else "",
                "thumbnail_url": f"/api/v1/media/alerts/{alert.id}/thumbnail" if alert.thumbnail_path else "",
                "camera_id": str(alert.camera_id) if alert.camera_id else "",
                "confidence": str(alert.confidence) if alert.confidence else "0"
            },
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="intrusion_alert_channel",
                    sound="alert_sound",
                    color="#FF0000",
                    icon="ic_launcher_foreground",
                    vibrate_timings=[0, 500, 1000, 500]
                )
            ),
            tokens=token_list
        )

        try:
            response = messaging.send_multicast(message)
            print(f"[FCM] Sent to {response.success_count} devices, {response.failure_count} failed")
            return response
        except Exception as e:
            print(f"[FCM] Error sending notification: {str(e)}")
            return None
