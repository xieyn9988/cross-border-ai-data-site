from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ScenarioRunRequest(BaseModel):
    params: Dict[str, Any] = Field(default_factory=dict)


class ScenarioRunResponse(BaseModel):
    scenario: str
    status: str
    output_file: Optional[str] = None
    message: Optional[str] = None


class UploadResponse(BaseModel):
    token: str
    filename: str
    size: int