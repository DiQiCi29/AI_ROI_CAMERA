from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AI_ROI_CAMERA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()