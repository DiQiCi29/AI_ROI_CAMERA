from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class BoundingBox(BaseModel):
    """A single bounding box in the detection result."""
    x: float = Field(..., ge=0, le=1280, description="X coordinate (0-1280 pixels)")
    y: float = Field(..., ge=0, le=720, description="Y coordinate (0-720 pixels)")
    w: float = Field(..., gt=0, le=1280, description="Width in pixels (>0-1280)")
    h: float = Field(..., gt=0, le=720, description="Height in pixels (>0-720)")
    label: str = Field(default="person", description="Object label/class name")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score (0-1)")

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not (0 <= v <= 1):
            raise ValueError('Confidence must be between 0 and 1')
        return v

    @field_validator('x', 'y', 'w', 'h')
    @classmethod
    def validate_coordinates(cls, v):
        if v < 0:
            raise ValueError('Coordinates must be non-negative')
        return v


class AlertCreate(BaseModel):
    """Schema for creating a new alert."""
    camera_id: int = Field(..., gt=0, description="Camera ID")
    zone_id: int = Field(..., gt=0, description="Zone ID")
    bounding_boxes: List[BoundingBox] = Field(default=[], description="List of detected objects")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall detection confidence")
    thumbnail_path: Optional[str] = Field(None, description="Path to alert thumbnail image")
    video_clip_path: Optional[str] = Field(None, description="Path to alert video clip")

    @field_validator('bounding_boxes')
    @classmethod
    def validate_bounding_boxes(cls, v):
        if not isinstance(v, list):
            raise ValueError('bounding_boxes must be a list')
        return v


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: int  # SỬA: Đổi từ alert_id: str thành id: int
    zone_id: Optional[int] = None # SỬA: Đổi str thành int
    zone_name: Optional[str] = None
    camera_id: Optional[int] = None # SỬA: Đổi str thành int
    detected_at: Optional[datetime] = None
    is_acknowledged: int = 0  # THÊM: Database đang dùng is_acknowledged, chứ không phải is_read
    thumbnail_path: Optional[str] = None # SỬA: Tên db là thumbnail_path chứ không phải thumbnail_url
    video_clip_path: Optional[str] = None # SỬA: Tên db là video_clip_path chứ không phải video_url
    confidence: Optional[float] = None
    bounding_boxes: Optional[list] = None

    class Config:
        from_attributes = True