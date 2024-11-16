from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship


class Paper(SQLModel, table=True):
    """
    文章/文件
    """
    __tablename__ = "paper"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    name: str = Field(index=True, description="文件名")

    file_size: int = Field(description="单位 B")
    page_size: int = Field(description="页数")

    criterion_tables_count: Optional[int] = Field(default=None, description="文件内解析出的表格数目（跨表视作多个）")
    criterion_tables: List["CandidateTable"] = Relationship(back_populates="paper")

    merged_criterion_table: Optional[List[List[str]]] = Field(default=None, sa_column=Column(JSON), description="合并后的目标表")
    merged_tables_count: Optional[int] = Field(default=None, description="合并表的来源表格数目")
    merged_rows_count: Optional[int] = Field(default=None, description="合并表后的总行数")
    merged_table_start_page: Optional[int] = None
    merged_table_end_page: Optional[int] = None

    publish_month: Optional[str] = Field(default=None, description="第一页解析出的发表月份")
    publish_month_verified: Optional[bool] = Field(default=False, description="是否已经尝试过解析第一页")


class CandidateTable(SQLModel, table=True):
    """
    用于确定目标表格的候选表格
    目标表格目前的生成算法：找到文件解析出的 N 个候选表格中连续最长的一组，然后合并
    """
    __tablename__ = "target_table"
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)

    paper: Paper = Relationship(back_populates="criterion_tables")
    paper_id: int = Field(foreign_key="paper.id")

    page: int = Field(description="该表格在文件中的页数（下标从 1 开始）")
    bbox: List[float] = Field(sa_column=Column(JSON), description="该表格在页面上的 bbox 格式坐标")
    raw_data: List[List[str]] = Field(sa_column=Column(JSON), description="该表格的二维数组数据")
    headers: List[str] = Field(sa_column=Column(JSON), description="该表格的列头，通常等于 raw_data 的第一行，但存在辅助列、跨行等问题")
