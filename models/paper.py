from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship


class Paper(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    name: str = Field(index=True)

    file_size: int
    page_size: int

    criterion_tables_count: Optional[int] = None
    criterion_tables: List["CandidateTable"] = Relationship(back_populates="paper")

    merged_criterion_table: Optional[List[List[str]]] = Field(default=None, sa_column=Column(JSON))
    merged_tables_count: Optional[int] = None
    merged_rows_count: Optional[int] = None


class CandidateTable(SQLModel, table=True):
    __tablename__ = "target_table"
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    paper: Paper = Relationship(back_populates="criterion_tables")
    paper_id: int = Field(foreign_key="paper.id")

    page: int
    bbox: List[float] = Field(sa_column=Column(JSON))
    raw_data: List[List[str]] = Field(sa_column=Column(JSON))
    headers: List[str] = Field(sa_column=Column(JSON))
