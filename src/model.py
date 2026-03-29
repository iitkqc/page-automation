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
    force_post: bool = False
    rejection_reason: Optional[str] = None

@dataclass
class ConfessionSelectionResponse:
    """Response schema for confession selection."""
    indices: List[int]
    admin_replies: List[str]
    funny_pinned_comments: List[str]
    empathetic_pinned_comments: List[str]
    discussion_pinned_comments: List[str]
    rejection_reasons: List[str]

@dataclass
class ModerationResponse:
    """Response schema for confession moderation."""
    is_safe: bool
    rejection_reason: str
    sentiment: str
    category: str
    summary_caption: str
    story_share_candidate: bool


@dataclass
class ManualPostEnhancementResponse:
    """Response schema for manual post caption/comment generation."""
    sentiment: str
    category: str
    summary_caption: str
    admin_reply: str
    funny_pinned_comment: str
    empathetic_pinned_comment: str
    discussion_pinned_comment: str
    story_share_candidate: bool
