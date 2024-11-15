import os
import pathlib
import re
import time

import pymupdf

from src.config import root_dir
from src.log import logger


def ensure_table(fp: str, progress_callback=None):
    """

    """
    doc = pymupdf.open(fp)
    total_pages = len(doc)

    if progress_callback:
        progress_callback(0, total_pages)

    candidate_tables = []
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
            headers = [i.strip().lower() for i in table.header.names if i]
            if (
                    'criterion' in headers
                    and 'summary assessment' in headers  # 筛选结果而非定义
            ):
                logger.info(f'page: {page_index}, headers: {headers}')
                candidate_tables.append(table)
            else:
                logger.debug(f'headers: {headers}')

    # 拿到候选 tables 集合之后，从中筛选出包含 `'criterion', 'summary assessment'`

    # logger.info(f'found table at page({start_page}-{end_page})')  # # logger.debug(f'table:\n{table_data.to_string()}')  # # logger.debug(f'table:\n{table_data.to_markdown()}')  # logger.debug(f"[Final Table]:\n{table_data.to_markdown(tablefmt='grid')}")  # # logger.debug(f"table:\n{tabulate(table_data, headers='keys', tablefmt='grid')}")  # return table_data, start_page, end_page


if __name__ == '__main__':
    start_index = 129
    files = [i for i in os.listdir(root_dir) if i.endswith(".pdf")]
    data = {"total": len(files), "skipped": start_index - 1}
    logger.info(f"Started Parsing: {data}")
    for index, fn in enumerate(sorted(files, key=lambda x: int(re.search(r'^\d+', x).group())), 1):
        if index >= start_index:
            fp = pathlib.Path(root_dir).joinpath(fn)
            logger.info(f'[{index} / {len(files)}] parsing {fp.as_uri()}')
            ensure_table(fp)
            time.sleep(0.1)
