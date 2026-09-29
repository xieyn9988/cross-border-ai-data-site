import os
import secrets

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..deps import get_config
from ..schemas import UploadResponse

router = APIRouter()

_UPLOAD_DIR_NAME = "uploads"


@router.post("/files/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:
    cfg = get_config()
    upload_dir = os.path.join(cfg["paths"]["data_dir"], _UPLOAD_DIR_NAME)
    os.makedirs(upload_dir, exist_ok=True)

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV")

    token = secrets.token_urlsafe(16)
    target = os.path.join(upload_dir, f"{token}_{file.filename}")
    content = await file.read()
    with open(target, "wb") as f:
        f.write(content)

    return UploadResponse(token=token, filename=file.filename, size=len(content))