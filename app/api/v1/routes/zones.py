from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.zone import Zone
from app.models.user import User
from app.schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse # Đã import ZoneResponse

router = APIRouter(prefix="/zones", tags=["Zone Management"])

# ĐÃ XÓA: Hàm zone_to_dict (Không còn cần thiết nữa)

def push_roi_to_detector(request: Request, db: Session, camera_id: int = 1):
    """Lấy tất cả các zone đang active của camera và cập nhật lên AI Detector"""
    if not hasattr(request.app.state, 'detector') or not request.app.state.detector:
        return

    # 1. Truy vấn lấy TẤT CẢ các vùng cấm đang kích hoạt của camera hiện tại
    active_zones = db.query(Zone).filter(
        Zone.is_active == True,
        Zone.camera_id == camera_id
    ).all()
    
    multi_rois_norm = []
    
    # 2. Duyệt qua từng vùng cấm, chuẩn hóa và đóng gói thành List các tọa độ
    for zone in active_zones:
        coords_norm = [
            (float(c["x"]), float(c["y"]))
            for c in zone.coordinates
        ]
        multi_rois_norm.append(coords_norm)

    # 3. Gửi mảng chứa nhiều Zone lên Detector (Dù mảng rỗng thì Detector sẽ tự động reset)
    request.app.state.detector.update_multi_roi(multi_rois_norm)
    print(f"[ROI] Updated {len(multi_rois_norm)} active zones to AI for Camera {camera_id}")

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
        push_roi_to_detector(request, db, zone.camera_id)

    # Trả về đối tượng Pydantic ZoneResponse
    return {"success": True, "data": ZoneResponse.model_validate(zone).model_dump()}


@router.get("")
def list_zones(camera_id: Optional[int] = None, is_active: Optional[bool] = None,
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    q = db.query(Zone)
    if camera_id: q = q.filter(Zone.camera_id == camera_id)
    if is_active is not None: q = q.filter(Zone.is_active == is_active)
    
    # Trả về List các đối tượng Pydantic ZoneResponse
    zones_response = [ZoneResponse.model_validate(z).model_dump() for z in q.all()]
    return {"success": True, "data": zones_response}


@router.get("/{zone_id}")
def get_zone(zone_id: int, db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail={
            "code": "ZONE_NOT_FOUND", "message": f"Zone {zone_id} not found"
        })
    return {"success": True, "data": ZoneResponse.model_validate(zone).model_dump()}


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
    push_roi_to_detector(request, db, zone.camera_id)

    return {"success": True, "data": ZoneResponse.model_validate(zone).model_dump()}


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
        # Nếu xóa hết zone, gửi một ROI trống để AI không bắt bất cứ gì
        request.app.state.detector.update_roi([])

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

    push_roi_to_detector(request, db, zone.camera_id)

    return {"success": True, "data": {"id": zone.id, "is_active": zone.is_active}}