from pydantic import BaseModel, Field
from typing import Optional


class AlertTriggerRequest(BaseModel):
    camera_id: int = Field(default=1, description="Camera ID")
    intruder_count: int = Field(default=1, ge=1, description="Số người xâm nhập")
    message: Optional[str] = Field(default=None, description="Ghi chú thêm")