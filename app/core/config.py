from pydantic_settings import BaseSettings
import secrets

class Settings(BaseSettings):
    APP_NAME: str = "AI_ROI_CAMERA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "duy273224605"
    DB_NAME: str = "ai_roi_camera"

    # Security
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-adminsdk.json"

    # Camera/Stream
    MEDIAMTX_HOST: str = "localhost"
    MEDIAMTX_PORT: int = 9997

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()