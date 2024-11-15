from sqlalchemy import select, null

from src.database import get_db
from models.paper import Paper

if __name__ == '__main__':
    with get_db() as session:
        rows = session.scalars(select(Paper).where(Paper.merged_criterion_table != None)).all()
        print(f'rows: {len(rows)}')

        for row in rows:
            row.merged_tables_count = None
            row.merged_rows_count = None
            row.merged_criterion_table = null()  # 不能用 None，会无效……
            session.add(row)

        session.commit()

        rows = session.scalars(select(Paper).where(Paper.merged_criterion_table != None)).all()
        print(f'rows: {len(rows)}')
