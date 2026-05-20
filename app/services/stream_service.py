"""
Stream Service
Contains business logic for camera streaming operations
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.camera import Camera, CameraStatus
from typing import List, Optional


class StreamService:
    """Service for handling camera stream operations"""

    @staticmethod
    def get_camera(camera_id: int, db: Session) -> Camera | None:
        """Get camera by ID"""
        return db.query(Camera).filter(Camera.id == camera_id).first()

    @staticmethod
    def get_all_cameras(active_only: bool = True, db: Session = None) -> List[Camera]:
        """
        Get all cameras
        
        Args:
            active_only: If True, only return active cameras
            db: Database session
            
        Returns:
            List of Camera objects
        """
        query = db.query(Camera)
        if active_only:
            query = query.filter(Camera.is_active == True)
        return query.all()

    @staticmethod
    def create_camera(name: str, rtsp_url: str, location: Optional[str] = None,
                     resolution: str = "1280x720", db: Session = None) -> Camera:
        """
        Create a new camera
        
        Args:
            name: Camera name
            rtsp_url: RTSP stream URL
            location: Camera location
            resolution: Video resolution (e.g., "1280x720")
            db: Database session
            
        Returns:
            Created Camera object
        """
        camera = Camera(
            name=name,
            rtsp_url=rtsp_url,
            location=location,
            resolution=resolution,
            status=CameraStatus.offline,
            is_active=True
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        return camera

    @staticmethod
    def update_camera_status(camera_id: int, status: CameraStatus, db: Session) -> bool:
        """Update camera online/offline status"""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.status = status
            camera.last_seen_at = datetime.utcnow()
            db.commit()
            return True
        return False

    @staticmethod
    def update_camera_rtsp_url(camera_id: int, rtsp_url: str, db: Session) -> bool:
        """Update camera RTSP URL"""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.rtsp_url = rtsp_url
            db.commit()
            return True
        return False

    @staticmethod
    def toggle_camera(camera_id: int, db: Session) -> bool:
        """Toggle camera active status"""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            camera.is_active = not camera.is_active
            db.commit()
            return True
        return False

    @staticmethod
    def delete_camera(camera_id: int, db: Session) -> bool:
        """Delete camera"""
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if camera:
            db.delete(camera)
            db.commit()
            return True
        return False

    @staticmethod
    def get_online_cameras(db: Session) -> List[Camera]:
        """Get all online cameras"""
        return db.query(Camera).filter(
            Camera.status == CameraStatus.online,
            Camera.is_active == True
        ).all()

    @staticmethod
    def get_offline_cameras(db: Session) -> List[Camera]:
        """Get all offline cameras"""
        return db.query(Camera).filter(
            Camera.status == CameraStatus.offline,
            Camera.is_active == True
        ).all()

    @staticmethod
    def parse_resolution(resolution: str) -> tuple:
        """
        Parse resolution string to (width, height)
        
        Args:
            resolution: Resolution string (e.g., "1280x720")
            
        Returns:
            Tuple of (width, height)
        """
        try:
            parts = resolution.split('x')
            return (int(parts[0]), int(parts[1]))
        except:
            return (1280, 720)  # Default resolution

    @staticmethod
    def validate_rtsp_url(rtsp_url: str) -> bool:
        """Validate RTSP URL format"""
        return rtsp_url.lower().startswith("rtsp://")

    @staticmethod
    def get_cameras_by_location(location: str, db: Session) -> List[Camera]:
        """Get cameras by location"""
        return db.query(Camera).filter(Camera.location == location).all()
