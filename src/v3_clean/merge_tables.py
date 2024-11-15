from sqlalchemy import select

from database import get_db
from models.paper import Paper
from src.log import logger


def merge_tables(paper: Paper):
    pass


if __name__ == '__main__':
    with get_db() as session:
        # 更新所有没有跑表的
        query = select(Paper).where(Paper.criterion_tables_count == None)
        papers = session.scalars(query).all()
        for (index, paper) in enumerate(papers[:]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper}")
            # candidate_tables = find_tables(paper, progress_callback=None)
            # paper.criterion_tables_count = len(candidate_tables) > 0
            # session.add_all(candidate_tables)
            # session.add(paper)


            session.commit()  # TODO: commit onKeyboard