import pandas as pd
from sqlmodel import select

from database import get_db
from src.config import PROJECT_ROOT, DATA_DIR
from src.log import logger
from models.paper import Paper
from src.utils.dataframe import data2df

if __name__ == '__main__':

    df = pd.DataFrame()

    with get_db() as session:
        # 更新所有没有跑表的
        query = select(Paper).where(Paper.merged_criterion_table == None,
                                    Paper.criterion_tables_count != None,
                                    Paper.criterion_tables_count > 0)
        papers = session.scalars(query).all()
        logger.info(f'papers count={len(papers)}')
        for (index, paper) in enumerate(papers[:3]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper}")

            table = paper.merged_criterion_table
            if not table:
                continue

            paper_df = data2df(table)
            paper_df['file_name'] = paper.name
            logger.info(f'paper[{index}] df:\n{paper_df.to_markdown(tablefmt="grid")}')
            df = pd.concat([df, paper_df], axis=1)

    df.to_excel(DATA_DIR / 'tables.xlsx', index=False)