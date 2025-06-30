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
