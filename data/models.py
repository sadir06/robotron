"""Pydantic models for QC event logging."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QCEvent(BaseModel):
    """Single classification + action event from the pipeline."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    item_id: int
    label: str  # GOOD | FAULTY | NOTHING
    raw_vlm_response: str
    vlm_latency_ms: float
    vlm_model: str
    action: Optional[str] = None  # left_pick | right_pick | None
    trajectory_file: Optional[str] = None  # which trajectory was replayed
    motor_positions_start: Optional[list[float]] = None
    motor_positions_end: Optional[list[float]] = None
    stability_frames: int = 1  # how many consecutive frames led to this
    outcome: Optional[str] = None  # success | failed | unverified
    frame_b64: Optional[str] = None  # base64 JPEG snapshot (optional)


class QCSessionStats(BaseModel):
    """Aggregated stats for a pipeline session."""

    session_id: str
    started_at: datetime
    total_items: int = 0
    good_count: int = 0
    faulty_count: int = 0
    nothing_count: int = 0
    avg_vlm_latency_ms: float = 0.0
    fault_rate: float = 0.0  # faulty / (good + faulty)
