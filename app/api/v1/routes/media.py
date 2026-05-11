from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.alert import Alert
from app.models.user import User
import os

router = APIRouter(prefix="/media", tags=["Media"])

@router.get("/alerts/{alert_id}/thumbnail")
def get_thumbnail(alert_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert or not alert.thumbnail_path:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    if not os.path.exists(alert.thumbnail_path):
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "File not found"})
    return FileResponse(alert.thumbnail_path, media_type="image/jpeg")

@router.get("/alerts/{alert_id}/video")
def get_video(alert_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert or not alert.video_clip_path:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    return FileResponse(alert.video_clip_path, media_type="video/mp4")

@router.delete("/alerts/{alert_id}")
def delete_media(alert_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Not found"})
    for path in [alert.thumbnail_path, alert.video_clip_path]:
        if path and os.path.exists(path):
            os.remove(path)
    alert.thumbnail_path = None
    alert.video_clip_path = None
    db.commit()
    return {"success": True, "message": "Media deleted successfully"}