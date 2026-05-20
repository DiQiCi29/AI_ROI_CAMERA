"""
Alert Service
Contains business logic for alert management and processing
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.models.alert import Alert
from app.models.intrusion_log import IntrusionLog
from app.models.zone import Zone
from app.models.camera import Camera
import json


class AlertService:
    """Service for handling alert operations"""

    @staticmethod
    def create_alert(camera_id: int, zone_id: int, bounding_boxes: List[Dict[str, Any]], 
                    confidence: float, thumbnail_path: Optional[str] = None,
                    video_clip_path: Optional[str] = None, db: Session = None) -> Alert:
        """
        Create a new intrusion alert
        
        Args:
            camera_id: Camera ID
            zone_id: Zone ID
            bounding_boxes: List of detected bounding boxes
            confidence: Detection confidence score
            thumbnail_path: Optional path to alert thumbnail
            video_clip_path: Optional path to alert video
            db: Database session
            
        Returns:
            Created Alert object
        """
        alert = Alert(
            camera_id=camera_id,
            zone_id=zone_id,
            bounding_boxes=json.dumps(bounding_boxes) if bounding_boxes else json.dumps([]),
            confidence=confidence,
            thumbnail_path=thumbnail_path,
            video_clip_path=video_clip_path,
            is_acknowledged=0,
            detected_at=datetime.utcnow()
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def get_alert(alert_id: int, db: Session) -> Alert | None:
        """Get alert by ID"""
        return db.query(Alert).filter(Alert.id == alert_id).first()

    @staticmethod
    def list_alerts(page: int = 1, limit: int = 20, zone_id: Optional[int] = None,
                   is_read: Optional[bool] = None, from_date: Optional[datetime] = None,
                   to_date: Optional[datetime] = None, db: Session = None) -> tuple:
        """
        List alerts with pagination and filters
        
        Returns:
            Tuple of (alerts, total_count)
        """
        query = db.query(Alert)
        
        if zone_id:
            query = query.filter(Alert.zone_id == zone_id)
        
        if is_read is not None:
            query = query.filter(Alert.is_acknowledged == (1 if is_read else 0))
        
        if from_date:
            query = query.filter(Alert.detected_at >= from_date)
        
        if to_date:
            query = query.filter(Alert.detected_at <= to_date)
        
        total = query.count()
        alerts = query.order_by(Alert.detected_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        return alerts, total

    @staticmethod
    def mark_as_read(alert_id: int, db: Session) -> bool:
        """Mark alert as read"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_acknowledged = 1
            db.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(db: Session) -> int:
        """Mark all unread alerts as read"""
        count = db.query(Alert).filter(Alert.is_acknowledged == 0).update({"is_acknowledged": 1})
        db.commit()
        return count

    @staticmethod
    def get_unread_count(db: Session) -> int:
        """Get count of unread alerts"""
        return db.query(Alert).filter(Alert.is_acknowledged == 0).count()

    @staticmethod
    def delete_alert(alert_id: int, db: Session) -> bool:
        """Delete alert and associated files"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            # Cascade delete will handle IntrusionLog
            db.delete(alert)
            db.commit()
            return True
        return False

    @staticmethod
    def check_alert_cooldown(zone_id: int, db: Session) -> bool:
        """
        Check if zone is in alert cooldown period
        
        Returns:
            True if cooldown active, False if can create new alert
        """
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return False
        
        cooldown_seconds = zone.alert_cooldown_seconds or 30
        cooldown_time = datetime.utcnow() - timedelta(seconds=cooldown_seconds)
        
        recent_alert = db.query(Alert).filter(
            Alert.zone_id == zone_id,
            Alert.detected_at >= cooldown_time
        ).first()
        
        return recent_alert is not None

    @staticmethod
    def get_bounding_box_count(alert_id: int, db: Session) -> int:
        """Get number of detected objects in alert"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert or not alert.bounding_boxes:
            return 0
        
        try:
            boxes = json.loads(alert.bounding_boxes) if isinstance(alert.bounding_boxes, str) else alert.bounding_boxes
            return len(boxes)
        except:
            return 0

    @staticmethod
    def get_alerts_by_zone(zone_id: int, days: int = 7, db: Session = None) -> List[Alert]:
        """Get all alerts for a zone in the last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        return db.query(Alert).filter(
            Alert.zone_id == zone_id,
            Alert.detected_at >= start_date
        ).order_by(Alert.detected_at.desc()).all()

    @staticmethod
    def get_alerts_by_camera(camera_id: int, days: int = 7, db: Session = None) -> List[Alert]:
        """Get all alerts for a camera in the last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        return db.query(Alert).filter(
            Alert.camera_id == camera_id,
            Alert.detected_at >= start_date
        ).order_by(Alert.detected_at.desc()).all()
