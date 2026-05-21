from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.zone import Zone
from app.models.user import User
from app.schemas.zone import ZoneCreate, ZoneUpdate

router = APIRouter(prefix="/zones", tags=["Zone Management"])

def zone_to_dict(z: Zone) -> dict:
    return {
        "zone_id": str(z.id),
        "name": z.name,
        "camera_id": z.camera_id,
        "zone_type": z.zone_type,
        "coordinates": z.coordinates,
        "is_active": z.is_active,
        "alert_cooldown_seconds": z.alert_cooldown_seconds or 30,
        "created_at": z.created_at,
        # "updated_at": z.updated_at,
    }

def push_roi_to_detector(request: Request, db: Session):
    """Lấy tất cả zone active và cập nhật ROI chuẩn hóa lên detector"""
    active_zone = db.query(Zone).filter(Zone.is_active == True).order_by(Zone.id.desc()).first()
    if not active_zone:
        return

    # Chỉ cần trích xuất dạng tuple (x, y) từ 0.0 - 1.0, KHÔNG nhân pixel nữa
    coords_norm = [
        (float(c["x"]), float(c["y"]))
        for c in active_zone.coordinates
    ]

    if hasattr(request.app.state, 'detector') and request.app.state.detector:
        detector = request.app.state.detector
        detector.update_roi(coords_norm)
        print(f"[ROI] Updated normalized coords to AI: {coords_norm}")


@router.post("", status_code=201)
def create_zone(body: ZoneCreate, request: Request,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    existing = db.query(Zone).filter(Zone.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": "ZONE_ALREADY_EXISTS", "message": "Zone name already exists"
        })
    zone = Zone(
        name=body.name,
        camera_id=body.camera_id,
        zone_type=body.zone_type,
        coordinates=[c.model_dump() for c in body.coordinates],
        is_active=body.is_active,
        alert_cooldown_seconds=body.alert_cooldown_seconds,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)

    # ── Tự động cập nhật ROI lên AI detector ──
    if zone.is_active:
        push_roi_to_detector(request, db)

    return {"success": True, "data": zone_to_dict(zone)}


@router.get("")
def list_zones(camera_id: Optional[int] = None, is_active: Optional[bool] = None,
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    q = db.query(Zone)
    if camera_id: q = q.filter(Zone.camera_id == camera_id)
    if is_active is not None: q = q.filter(Zone.is_active == is_active)
    return {"success": True, "data": [zone_to_dict(z) for z in q.all()]}


@router.get("/{zone_id}")
def get_zone(zone_id: int, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": f"Zone {zone_id} not found"
        })
    return {"success": True, "data": zone_to_dict(zone)}


@router.put("/{zone_id}")
def update_zone(zone_id: int, body: ZoneUpdate, request: Request,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": "Not found"
        })
    if body.name is not None: zone.name = body.name
    if body.coordinates is not None:
        zone.coordinates = [c.model_dump() for c in body.coordinates]
    if body.is_active is not None: zone.is_active = body.is_active
    if body.alert_cooldown_seconds is not None:
        zone.alert_cooldown_seconds = body.alert_cooldown_seconds
    db.commit()
    db.refresh(zone)

    # ── Tự động cập nhật ROI lên AI detector ──
    push_roi_to_detector(request, db)

    return {"success": True, "data": zone_to_dict(zone)}


@router.delete("/{zone_id}")
def delete_zone(zone_id: int, request: Request,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": "Not found"
        })
    db.delete(zone)
    db.commit()

    # Reset về ROI mặc định nếu xóa hết zone
    remaining = db.query(Zone).filter(Zone.is_active == True).count()
    if remaining == 0:
        request.app.state.detector.update_roi([
            (0, 0), (1280, 0), (1280, 720), (0, 720)
        ])

    return {"success": True, "message": "Zone deleted successfully"}


@router.patch("/{zone_id}/toggle")
def toggle_zone(zone_id: int, request: Request,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": "Not found"
        })
    zone.is_active = not zone.is_active
    db.commit()

    push_roi_to_detector(request, db)

    return {"success": True, "data": {"zone_id": str(zone.id), "is_active": zone.is_active}}