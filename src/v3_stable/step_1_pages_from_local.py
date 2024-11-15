from pymupdf import pymupdf
from sqlmodel import select

from src.database import get_db
from src.models import Paper
from src.config import SORTED_FILES
from src.log import logger

if __name__ == '__main__':
    with get_db() as session:
        n = 0
        for index, file in enumerate(SORTED_FILES, 1):
            logger.debug(f"handling [{index} / {len(SORTED_FILES)}] fn: {file.name}")

            paper = session.scalar(select(Paper).where(Paper.name == file.name))
            # 跳过已经完成的
            if paper:
                continue

            n += 1
            logger.info(f"--> adding {n}")
            doc = pymupdf.open(file)
            page_size = len(doc)
            paper = Paper(id=n, name=file.name, file_size=file.__sizeof__(), page_size=page_size)
            session.add(paper)
        session.commit()
