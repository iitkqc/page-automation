from typing import Optional, List
from dataclasses import dataclass

@dataclass
class Confession:
    timestamp: str
    row_num: int
    text: str
    summary_caption: Optional[str] = None
    sentiment: Optional[str] = None
    sigma_reply: Optional[str] = None
    count: Optional[int] = None

@dataclass
class ConfessionSelectionResponse:
    """Response schema for confession selection."""
    indices: List[int]
    admin_replies: List[str]

@dataclass
class ModerationResponse:
    """Response schema for confession moderation."""
    is_safe: bool
    rejection_reason: str
    sentiment: str
    summary_caption: str