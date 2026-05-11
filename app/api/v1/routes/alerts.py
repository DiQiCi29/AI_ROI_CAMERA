from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.alert import Alert
from app.models.zone import Zone
from app.models.user import User
import math

router = APIRouter(prefix="/alerts", tags=["Alerts"])

def alert_to_dict(a: Alert, include_bbox=False) -> dict:
    base = {
        "alert_id": str(a.id),
        "zone_id": str(a.zone_id) if a.zone_id else None,
        "camera_id": str(a.camera_id) if a.camera_id else None,
        "detected_at": a.detected_at,
        "is_read": bool(a.is_acknowledged),
        "thumbnail_url": f"/api/v1/media/alerts/{a.id}/thumbnail" if a.thumbnail_path else None,
        "video_url": f"/api/v1/media/alerts/{a.id}/video" if a.video_clip_path else None,
        "object_count": 1,
        "confidence": a.confidence,
    }
    if include_bbox:
        base["bounding_boxes"] = a.bounding_boxes or []
    return base

@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    count = db.query(Alert).filter(Alert.is_acknowledged == 0).count()
    return {"success": True, "data": {"unread_count": count}}

@router.patch("/read-all")
def read_all(db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    db.query(Alert).filter(Alert.is_acknowledged == 0).update({"is_acknowledged": 1})
    db.commit()
    return {"success": True, "message": "All alerts marked as read"}

@router.get("")
def list_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    zone_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Alert)
    if zone_id: q = q.filter(Alert.zone_id == zone_id)
    if is_read is not None: q = q.filter(Alert.is_acknowledged == (1 if is_read else 0))
    if from_date: q = q.filter(Alert.detected_at >= from_date)
    if to_date: q = q.filter(Alert.detected_at <= to_date)
    total = q.count()
    items = q.order_by(Alert.detected_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"success": True, "data": {
        "items": [alert_to_dict(a) for a in items],
        "pagination": {"page": page, "limit": limit, "total": total,
                       "total_pages": math.ceil(total / limit)}
    }}

@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    return {"success": True, "data": alert_to_dict(a, include_bbox=True)}

@router.patch("/{alert_id}/read")
def mark_read(alert_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    a.is_acknowledged = 1
    db.commit()
    return {"success": True, "data": {"alert_id": str(a.id), "is_read": True}}