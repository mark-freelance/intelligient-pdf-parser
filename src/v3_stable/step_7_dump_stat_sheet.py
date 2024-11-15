import pandas as pd
from sqlmodel import select

from src.models import Paper
from src.config import DATA_DIR, PROJECT_STAT_SHEET_NAME
from src.database import get_db

if __name__ == '__main__':
    with get_db() as session:
        items = []
        for paper in session.scalars(select(Paper)).all():
            item = paper.model_dump(exclude={'merged_criterion_table'})
            items.append(item)
        df = pd.DataFrame(items)
        df.to_excel(DATA_DIR / PROJECT_STAT_SHEET_NAME)
