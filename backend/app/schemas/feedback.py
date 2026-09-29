from typing import Optional
from pydantic import BaseModel


class FeedbackIn(BaseModel):
    scene: str                 # briefing / assist / followup / chat
    rating: str                # up / down
    source: str                # 来源卡 source 字段
    label: Optional[str] = None
    customer_id: Optional[int] = None
    comment: Optional[str] = None
