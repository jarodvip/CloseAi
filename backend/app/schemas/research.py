from typing import Optional

from pydantic import BaseModel


class ImportUrlIn(BaseModel):
    """内网页面抓取入参"""
    url: str
    industry: Optional[str] = None
    source_name: Optional[str] = None
