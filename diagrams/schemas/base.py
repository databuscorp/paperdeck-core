"""
Base Pydantic schemas for the STEM diagram rendering engine.
All diagram schemas inherit from DiagramSchema.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DiagramType(str, Enum):
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    MATHEMATICS = "mathematics"
    CIRCUITS = "circuits"
    BIOLOGY = "biology"


class Canvas(BaseModel):
    width: int = Field(default=800, ge=100, le=4096)
    height: int = Field(default=600, ge=100, le=4096)


class Annotation(BaseModel):
    text: str
    x: Optional[float] = None
    y: Optional[float] = None
    font_size: int = Field(default=14, ge=6, le=72)
    color: str = "black"
    anchor: str = "middle"  # start | middle | end


class DiagramSchema(BaseModel):
    """Master diagram schema — all sub-types validate against this first."""
    diagram_type: DiagramType
    subtype: str
    canvas: Canvas = Field(default_factory=Canvas)
    objects: List[Dict[str, Any]] = Field(default_factory=list)
    annotations: List[Annotation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("subtype")
    @classmethod
    def subtype_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("subtype must not be empty")
        return v.lower().strip()

    model_config = {"use_enum_values": True}
