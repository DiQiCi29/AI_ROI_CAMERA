from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.intrusion_log import IntrusionLog
from app.models.alert import Alert
from app.models.zone import Zone
from app.models.user import User
import math

router = APIRouter(prefix="/logs", tags=["Intrusion Logs"])

@router.get("")
def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    zone_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(IntrusionLog)
    if zone_id: q = q.filter(IntrusionLog.camera_id == zone_id)
    if from_date: q = q.filter(IntrusionLog.entered_at >= from_date)
    if to_date: q = q.filter(IntrusionLog.entered_at <= to_date)
    total = q.count()
    items = q.order_by(IntrusionLog.entered_at.desc()).offset((page - 1) * limit).limit(limit).all()

    def log_dict(l):
        alert = db.query(Alert).filter(Alert.id == l.alert_id).first()
        return {
            "log_id": str(l.id),
            "alert_id": str(l.alert_id),
            "camera_id": str(l.camera_id) if l.camera_id else None,
            "zone_id": str(l.zone_id) if l.zone_id else None,
            "entered_at": l.entered_at,
            "exited_at": l.exited_at,
            "duration_seconds": l.duration_seconds,
            "thumbnail_url": f"/api/v1/media/alerts/{l.alert_id}/thumbnail" if alert and alert.thumbnail_path else None,
            "video_url": f"/api/v1/media/alerts/{l.alert_id}/video" if alert and alert.video_clip_path else None,
        }

    return {"success": True, "data": {
        "items": [log_dict(l) for l in items],
        "pagination": {"page": page, "limit": limit, "total": total,
                       "total_pages": math.ceil(total / limit)}
    }}

@router.get("/stats")
def get_stats(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Thống kê xâm nhập với đầy đủ dữ liệu analytics
    """
    q = db.query(IntrusionLog)
    if from_date:
        q = q.filter(IntrusionLog.entered_at >= from_date)
    if to_date:
        q = q.filter(IntrusionLog.entered_at <= to_date)

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    # Basic counts
    total = q.count()
    today_count = q.filter(func.date(IntrusionLog.entered_at) == today).count()
    week_count = q.filter(
        func.date(IntrusionLog.entered_at) >= week_ago,
        func.date(IntrusionLog.entered_at) <= today
    ).count()
    
    # Most active zone (join through Alert to get zone_id)
    most_active_query = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        Alert, Alert.id == IntrusionLog.alert_id
    ).outerjoin(
        Zone, Zone.id == Alert.zone_id
    ).group_by(Zone.id).order_by(func.count(IntrusionLog.id).desc()).first()
    
    most_active = None
    if most_active_query:
        most_active = {
            "zone_id": str(most_active_query[0]),
            "zone_name": most_active_query[1],
            "count": most_active_query[2] or 0
        }
    
    # By zone breakdown
    by_zone_query = db.query(
        Zone.id,
        Zone.name,
        func.count(IntrusionLog.id).label('count')
    ).outerjoin(
        Alert, Alert.id == IntrusionLog.alert_id
    ).outerjoin(
        Zone, Zone.id == Alert.zone_id
    ).group_by(Zone.id).all()
    
    by_zone = [
        {
            "zone_id": str(z[0]),
            "zone_name": z[1],
            "count": z[2] or 0
        }
        for z in by_zone_query
    ]
    
    # Peak hour (hour with most intrusions)
    peak_hour_query = db.query(
        extract('hour', IntrusionLog.entered_at).label('hour'),
        func.count(IntrusionLog.id).label('count')
    ).group_by('hour').order_by(func.count(IntrusionLog.id).desc()).first()
    
    peak_hour = None
    if peak_hour_query:
        peak_hour = int(peak_hour_query[0])

    return {"success": True, "data": {
        "total_intrusions": total,
        "intrusions_today": today_count,
        "intrusions_this_week": week_count,
        "most_active_zone": most_active,
        "peak_hour": peak_hour,
        "by_zone": by_zone
    }}