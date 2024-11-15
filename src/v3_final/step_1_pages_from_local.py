import os

from pymupdf import pymupdf
from sqlmodel import select

from database import get_db
from models.paper import Paper
from src.config import sorted_file_names, root_dir
from src.log import logger

if __name__ == '__main__':
    with get_db() as session:
        n = 0
        for index, fn in enumerate(sorted_file_names, 1):
            logger.debug(f"handling [{index} / {len(sorted_file_names)}] fn: {fn}")

            paper = session.scalar(select(Paper).where(Paper.name == fn))
            # 跳过已经完成的
            if paper:
                continue

            n += 1
            logger.info(f"--> adding {n}")
            fp = os.path.join(root_dir, fn)
            file_size = os.path.getsize(fp)
            doc = pymupdf.open(fp)
            page_size = len(doc)
            paper = Paper(name=fn, file_size=file_size, page_size=page_size, id=n)
            session.add(paper)
        session.commit()
