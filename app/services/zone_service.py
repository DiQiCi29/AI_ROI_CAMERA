"""
Zone Service
Contains business logic for zone management and ROI operations
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from app.models.zone import Zone
from app.models.camera import Camera
import json


class ZoneService:
    """Service for handling zone operations"""

    @staticmethod
    def create_zone(name: str, camera_id: int, zone_type: str, 
                   coordinates: List[Dict[str, float]], is_active: bool = True,
                   alert_cooldown_seconds: int = 30, db: Session = None) -> Zone:
        """
        Create a new detection zone
        
        Args:
            name: Zone name
            camera_id: Camera ID
            zone_type: "polygon" or "rectangle"
            coordinates: List of {x: 0-100, y: 0-100} coordinates
            is_active: Enable zone
            alert_cooldown_seconds: Cooldown between alerts
            db: Database session
            
        Returns:
            Created Zone object
        """
        zone = Zone(
            name=name,
            camera_id=camera_id,
            zone_type=zone_type,
            coordinates=json.dumps(coordinates),
            is_active=is_active,
            alert_cooldown_seconds=alert_cooldown_seconds,
            created_at=datetime.utcnow()
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)
        return zone

    @staticmethod
    def get_zone(zone_id: int, db: Session) -> Zone | None:
        """Get zone by ID"""
        return db.query(Zone).filter(Zone.id == zone_id).first()

    @staticmethod
    def list_zones(camera_id: Optional[int] = None, is_active: Optional[bool] = None, 
                  db: Session = None) -> List[Zone]:
        """
        List all zones with optional filters
        
        Args:
            camera_id: Filter by camera
            is_active: Filter by active status
            db: Database session
            
        Returns:
            List of Zone objects
        """
        query = db.query(Zone)
        
        if camera_id is not None:
            query = query.filter(Zone.camera_id == camera_id)
        
        if is_active is not None:
            query = query.filter(Zone.is_active == is_active)
        
        return query.order_by(Zone.created_at.desc()).all()

    @staticmethod
    def update_zone(zone_id: int, name: Optional[str] = None,
                   coordinates: Optional[List[Dict[str, float]]] = None,
                   is_active: Optional[bool] = None,
                   alert_cooldown_seconds: Optional[int] = None,
                   db: Session = None) -> Zone | None:
        """
        Update zone properties
        
        Args:
            zone_id: Zone ID
            name: New name (optional)
            coordinates: New coordinates (optional)
            is_active: New active status (optional)
            alert_cooldown_seconds: New cooldown (optional)
            db: Database session
            
        Returns:
            Updated Zone object or None if not found
        """
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return None
        
        if name is not None:
            zone.name = name
        
        if coordinates is not None:
            zone.coordinates = json.dumps(coordinates)
        
        if is_active is not None:
            zone.is_active = is_active
        
        if alert_cooldown_seconds is not None:
            zone.alert_cooldown_seconds = alert_cooldown_seconds
        
        # zone.updated_at = datetime.utcnow()  # Removed: column deleted from database
        db.commit()
        db.refresh(zone)
        return zone

    @staticmethod
    def delete_zone(zone_id: int, db: Session) -> bool:
        """Delete zone"""
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if zone:
            db.delete(zone)
            db.commit()
            return True
        return False

    @staticmethod
    def toggle_zone_active(zone_id: int, db: Session) -> bool:
        """Toggle zone active/inactive status"""
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if zone:
            zone.is_active = not zone.is_active
            # zone.updated_at = datetime.utcnow()  # Removed: column deleted from database
            db.commit()
            return True
        return False

    @staticmethod
    def get_zone_roi_pixels(zone_id: int, db: Session) -> Tuple[List[Tuple[int, int]], Tuple[int, int]]:
        zone = db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return None
        
        frame_width, frame_height = 1280, 720
        
        try:
            coords = json.loads(zone.coordinates) if isinstance(zone.coordinates, str) else zone.coordinates
            
            pixel_coords = []
            for coord in coords:
                # Không cần chia cho 100.0 nữa, chỉ cần nhân trực tiếp với tỉ lệ
                pixel_x = int(coord['x'] * frame_width)
                pixel_y = int(coord['y'] * frame_height)
                pixel_coords.append((pixel_x, pixel_y))
            
            return pixel_coords, (frame_width, frame_height)
        except Exception:
            return None

    @staticmethod
    def get_active_zones_for_camera(camera_id: int, db: Session) -> List[Zone]:
        """Get all active zones for a specific camera"""
        return db.query(Zone).filter(
            Zone.camera_id == camera_id,
            Zone.is_active == True
        ).all()

    @staticmethod
    def validate_coordinates(coordinates: List[Dict[str, float]]) -> bool:
        if not coordinates or len(coordinates) < 3:
            return False
        
        for coord in coordinates:
            # Đổi khoảng kiểm tra thành 0.0 đến 1.0
            if not (0.0 <= coord.get('x', -1.0) <= 1.0 and 0.0 <= coord.get('y', -1.0) <= 1.0):
                return False
        
        return True

    @staticmethod
    def get_default_roi() -> List[Dict[str, float]]:
        # Đổi tọa độ mặc định thành chuẩn hóa
        return [
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
            {"x": 0.0, "y": 1.0}
        ]

    @staticmethod
    def calculate_roi_from_zones(camera_id: int, db: Session) -> List[Dict[str, float]]:
        """
        Calculate combined ROI from all active zones for a camera
        
        Returns default ROI if no active zones
        """
        zones = ZoneService.get_active_zones_for_camera(camera_id, db)
        
        if not zones:
            return ZoneService.get_default_roi()
        
        # For simplicity, return first active zone's coordinates
        # In production, could implement zone union logic
        if zones:
            try:
                coords = json.loads(zones[0].coordinates) if isinstance(zones[0].coordinates, str) else zones[0].coordinates
                return coords
            except:
                pass
        
        return ZoneService.get_default_roi()

    @staticmethod
    def get_zones_by_name(name_pattern: str, db: Session) -> List[Zone]:
        """Search zones by name pattern"""
        return db.query(Zone).filter(Zone.name.ilike(f"%{name_pattern}%")).all()

    @staticmethod
    def get_zone_count_by_camera(camera_id: int, db: Session) -> int:
        """Get total zone count for a camera"""
        return db.query(Zone).filter(Zone.camera_id == camera_id).count()

    @staticmethod
    def get_active_zone_count_by_camera(camera_id: int, db: Session) -> int:
        """Get active zone count for a camera"""
        return db.query(Zone).filter(
            Zone.camera_id == camera_id,
            Zone.is_active == True
        ).count()
