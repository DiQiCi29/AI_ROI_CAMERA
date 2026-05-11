from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

class Coordinate(BaseModel):
    x: float
    y: float

class ZoneCreate(BaseModel):
    name: str
    camera_id: str
    zone_type: str = "polygon"
    coordinates: List[Coordinate]
    is_active: bool = True
    alert_cooldown_seconds: int = 30

    @field_validator("coordinates")
    def validate_coords(cls, coords):
        for c in coords:
            if not (0 <= c.x <= 100 and 0 <= c.y <= 100):
                raise ValueError("Coordinates must be between 0 and 100 (%)")
        return coords

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    coordinates: Optional[List[Coordinate]] = None
    is_active: Optional[bool] = None
    alert_cooldown_seconds: Optional[int] = None

class ZoneResponse(BaseModel):
    zone_id: str
    name: str
    camera_id: str
    zone_type: str
    coordinates: list
    is_active: bool
    alert_cooldown_seconds: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True