import pandas as pd
from sqlmodel import select

from src.config import DATA_DIR, PROJECT_STAT_SHEET_NAME
from src.database import get_db
from src.models import Paper


def step_7_dump_stat_sheet():
    with get_db() as session:
        items = []
        for paper in session.scalars(select(Paper)).all():
            item = paper.model_dump(exclude={'merged_criterion_table'})
            items.append(item)
        df = pd.DataFrame(items)
        df.to_excel(DATA_DIR / PROJECT_STAT_SHEET_NAME)


if __name__ == '__main__':
    step_7_dump_stat_sheet()
