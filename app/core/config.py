from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AI_ROI_CAMERA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "258463"
    DB_NAME: str = "AI_ROI_CAMERA"

    # MQTT Broker
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str = "mqtt_user"
    MQTT_PASSWORD: str = "mqtt_pass"
    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()