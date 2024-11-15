import os
from datetime import datetime

import pymupdf
from sqlalchemy import select

from database import get_db
from models.paper import Paper
from src.config import sorted_file_names, root_dir

if __name__ == '__main__':

    with get_db() as session:

        # action = 'init'
        action = 'update'


        def batch_handle(index, fn):
            print(index, fn)
            fp = os.path.join(root_dir, fn)
            file_size = os.path.getsize(fp)
            doc = pymupdf.open(fp)
            page_size = len(doc)

            if action == "init":
                item = Paper(name=fn, file_size=file_size, page_size=page_size)

            elif action == "update":
                item = session.scalar(select(Paper).where(Paper.name == fn))
                item.updated_at = datetime.utcnow()
                print(item)
            return item


        items = [batch_handle(*args) for args in enumerate(sorted_file_names)]
        session.add_all(items)
        session.commit()
