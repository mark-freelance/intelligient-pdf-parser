from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class Paper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    name: str = Field(index=True)

    file_size: int
    page_size: int
