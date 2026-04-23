from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskResponse(BaseModel):
    id: int
    engine_id: int
    version_type: str
    original_filename: str
    req_doc_text: str
    status: str
    progress: int
    output_path: Optional[str]
    log_text: str
    error_msg: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
