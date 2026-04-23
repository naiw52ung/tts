from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile

from app.core.config import settings


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def task_root(task_id: int) -> Path:
    return ensure_dir(Path(settings.storage_root) / f"task_{task_id}")


async def save_upload(task_id: int, upload: UploadFile) -> str:
    root = task_root(task_id)
    ext = Path(upload.filename or "").suffix.lower()
    filename = f"source_{uuid4().hex}{ext}"
    path = root / filename
    async with aiofiles.open(path, "wb") as f:
        while chunk := await upload.read(1024 * 1024):
            await f.write(chunk)
    await upload.close()
    return str(path)
