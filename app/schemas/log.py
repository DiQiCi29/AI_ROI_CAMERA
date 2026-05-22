"""
Log Schemas
Pydantic models for intrusion logs and analytics
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class BoundingBoxInLog(BaseModel):
    """Bounding box stored in log"""
    x: float
    y: float
    w: float
    h: float
    label: str
    confidence: float


class IntrusionLogCreate(BaseModel):
    """Schema for creating intrusion log"""
    alert_id: int = Field(..., gt=0, description="Alert ID")
    camera_id: int = Field(..., gt=0, description="Camera ID")
    zone_id: Optional[int] = Field(None, description="Zone ID")
    entered_at: datetime = Field(..., description="When intrusion started")
    exited_at: Optional[datetime] = Field(None, description="When intrusion ended")


class IntrusionLogResponse(BaseModel):
    """Schema for intrusion log response"""
    id: int # SỬA: Đổi từ log_id: str thành id: int
    alert_id: int # SỬA: Đổi str thành int
    camera_id: Optional[int] = None # SỬA: Đổi str thành int và thêm Optional vì db cho phép nullable
    zone_id: Optional[int] = None # SỬA: Giữ nguyên Optional nhưng đổi str thành int
    zone_name: Optional[str] = None
    entered_at: datetime
    exited_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class IntrusionLogListResponse(BaseModel):
    """Schema for paginated intrusion logs"""
    items: List[IntrusionLogResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class StatsData(BaseModel):
    """Schema for analytics dashboard"""
    total_intrusions: int = Field(..., ge=0, description="Total intrusions")
    intrusions_today: int = Field(..., ge=0, description="Intrusions in current day")
    intrusions_this_week: int = Field(..., ge=0, description="Intrusions in current week")
    most_active_zone: Optional[str] = Field(None, description="Zone with most intrusions")
    peak_hour: Optional[int] = Field(None, ge=0, le=23, description="Hour with most intrusions")
    by_zone: Dict[str, int] = Field(default_factory=dict, description="Breakdown by zone")
    by_camera: Optional[Dict[str, int]] = Field(None, description="Breakdown by camera")
    by_hour: Optional[Dict[int, int]] = Field(None, description="Hourly breakdown")
    by_day: Optional[Dict[str, int]] = Field(None, description="Daily breakdown")


class AnalyticsFilter(BaseModel):
    """Filter parameters for analytics"""
    from_date: Optional[datetime] = Field(None, description="Start date (ISO 8601)")
    to_date: Optional[datetime] = Field(None, description="End date (ISO 8601)")
    camera_id: Optional[int] = Field(None, description="Camera ID")
    zone_id: Optional[int] = Field(None, description="Zone ID")
    group_by: Optional[str] = Field("none", description="Group by: none|hour|day|week|month")


class HourlyStats(BaseModel):
    """Hourly statistics"""
    hour: int = Field(..., ge=0, le=23, description="Hour of day")
    intrusions: int = Field(..., ge=0, description="Number of intrusions")
    zones_affected: int = Field(..., ge=0, description="Number of zones affected")


class DailyStats(BaseModel):
    """Daily statistics"""
    date: datetime
    intrusions: int = Field(..., ge=0, description="Number of intrusions")
    zones_affected: int = Field(..., ge=0, description="Number of zones affected")
    cameras_involved: int = Field(..., ge=0, description="Number of cameras involved")


class ZoneStatsDetail(BaseModel):
    """Detailed stats for a zone"""
    zone_id: int
    zone_name: str
    camera_id: int
    total_intrusions: int = Field(..., ge=0)
    intrusions_today: int = Field(..., ge=0)
    last_intrusion: Optional[datetime] = None
    average_duration_seconds: Optional[int] = None
    confidence_avg: Optional[float] = Field(None, ge=0.0, le=1.0)


class CameraStatsDetail(BaseModel):
    """Detailed stats for a camera"""
    camera_id: int
    camera_name: str
    total_intrusions: int = Field(..., ge=0)
    active_zones: int = Field(..., ge=0)
    zones_with_activity: List[str] = Field(default_factory=list)
    last_intrusion: Optional[datetime] = None


class AdvancedStats(BaseModel):
    """Advanced analytics response"""
    summary: StatsData
    hourly: Optional[List[HourlyStats]] = None
    daily: Optional[List[DailyStats]] = None
    zones: Optional[List[ZoneStatsDetail]] = None
    cameras: Optional[List[CameraStatsDetail]] = None
    time_range: Dict[str, datetime] = Field(..., description="Query time range")


class TimeSeriesPoint(BaseModel):
    """Single data point in time series"""
    timestamp: datetime
    value: int = Field(..., ge=0, description="Event count at this point")
    zones_affected: int = Field(..., ge=0, description="Zones affected at this point")


class TimeSeriesData(BaseModel):
    """Time series analytics data"""
    label: str = Field(..., description="Series label")
    data: List[TimeSeriesPoint]
    interval: str = Field(..., description="Interval: hourly|daily|weekly")
    aggregation: str = Field(..., description="Aggregation method: sum|avg|max|min")
