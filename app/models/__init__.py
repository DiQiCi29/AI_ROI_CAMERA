# Import tất cả để SQLAlchemy biết tạo bảng nào
from app.models.user import User
from app.models.fcm_token import FCMToken
from app.models.camera import Camera
from app.models.zone import Zone
from app.models.alert import Alert
from app.models.intrusion_log import IntrusionLog
from app.models.device import Device
from app.models.notification_log import NotificationLog