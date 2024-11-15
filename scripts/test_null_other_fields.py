from sqlalchemy import select

from src.database import get_db
from models.paper import Paper

if __name__ == '__main__':
    with get_db() as session:
        rows = session.scalars(select(Paper).where(Paper.merged_tables_count != None)).all()
        print(f'rows: {len(rows)}')

