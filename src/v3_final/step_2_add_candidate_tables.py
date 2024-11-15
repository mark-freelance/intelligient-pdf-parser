import pathlib
from typing import List

import pymupdf
from sqlmodel import select

from database import get_db
from models.paper import Paper, CandidateTable
from src.config import root_dir
from src.log import logger


def init_candidate_tables(paper: Paper, progress_callback=None):
    fn = paper.name
    fp = pathlib.Path(root_dir).joinpath(fn)
    doc = pymupdf.open(fp)
    total_pages = len(doc)

    if progress_callback:
        progress_callback(0, total_pages)

    candidate_tables: List[CandidateTable] = []
    for page_index, page in enumerate(doc, 1):
        logger.debug(f'  page {page_index}')
        if progress_callback:
            progress_callback(page_index, total_pages)

        try:
            tables = page.find_tables()
        except Exception as e:
            if "not a textpage" in str(e).lower():
                continue
            else:
                raise e

        for table in tables:
            headers = [i.lower().strip() for i in table.header.names if i]
            if "criterion" in headers:
                logger.info(f'page: {page_index}, headers: {headers}')
                raw_data = table.extract()
                candidate_table = CandidateTable(paper=paper,
                                                 page=page_index,
                                                 bbox=table.bbox,
                                                 raw_data=raw_data,
                                                 headers=headers)
                candidate_tables.append(candidate_table)

    paper.criterion_tables_count = len(candidate_tables)
    return paper, candidate_tables


if __name__ == '__main__':
    with get_db() as session:
        query = select(Paper).where(Paper.criterion_tables_count == None)
        papers = session.scalars(query).all()
        for (index, paper) in enumerate(papers[:]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper}")
            paper, candidate_tables = init_candidate_tables(paper, progress_callback=None)
            session.add(paper)
            session.add_all(candidate_tables)
            session.commit()
