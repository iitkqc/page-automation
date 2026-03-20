from typing import Optional, List
from dataclasses import dataclass

@dataclass
class Confession:
    timestamp: str
    row_num: int
    text: str
    summary_caption: Optional[str] = None
    sentiment: Optional[str] = None
    category: Optional[str] = None
    sigma_reply: Optional[str] = None
    pinned_comments: Optional[dict[str, str]] = None
    count: Optional[int] = None
    story_share_candidate: bool = False

@dataclass
class ConfessionSelectionResponse:
    """Response schema for confession selection."""
    indices: List[int]
    admin_replies: List[str]
    funny_pinned_comments: List[str]
    empathetic_pinned_comments: List[str]
    discussion_pinned_comments: List[str]

@dataclass
class ModerationResponse:
    """Response schema for confession moderation."""
    is_safe: bool
    rejection_reason: str
    sentiment: str
    category: str
    summary_caption: str
    story_share_candidate: bool
