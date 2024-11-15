import os
import pathlib
import re
import time

import pandas as pd
import pymupdf

from src.config import root_dir
from src.log import logger
from src.utils.format_merged_cells_table import format_merged_cells_table


def ensure_table(fp: str, progress_callback=None):
    doc = pymupdf.open(fp)
    total_pages = len(doc)

    if progress_callback:
        progress_callback(0, total_pages)

    table_data = None
    last_header_names = None
    start_page = None
    end_page = None

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
            rows = table.to_pandas()

            header_names = [i for i in table.header.names  # fix empty cols (invisible but exists)
                            if not i.startswith('Col')]
            logger.debug(f'  found table in page({page_index}), header_names:\n{header_names}')

            if 'criterion' in [i.strip().lower() for i in header_names]:
                logger.debug(f"[Realtime Table]:\n{rows.to_markdown(tablefmt='grid')}")
                if header_names != last_header_names:
                    if last_header_names is not None:
                        logger.warning(f"[DUPLICATE], last table at page({start_page}-{end_page}), current page at {page_index}")
                        return None

                    table_data = rows
                    start_page = page_index
                else:
                    table_data = pd.concat([table_data, rows], axis=0)

                last_header_names = header_names
                end_page = page_index

    if table_data is None:
        logger.warning("failed to find table")
        return None

    logger.info(f'found table at page({start_page}-{end_page})')
    # logger.debug(f'table:\n{table_data.to_string()}')
    # logger.debug(f'table:\n{table_data.to_markdown()}')
    logger.debug(f"[Final Table]:\n{table_data.to_markdown(tablefmt='grid')}")
    # logger.debug(f"table:\n{tabulate(table_data, headers='keys', tablefmt='grid')}")
    # logger.debug(f"table:\n{format_merged_cells_table(table_data)}")
    return table_data, start_page, end_page


if __name__ == '__main__':
    start_index = 10
    files = [i for i in os.listdir(root_dir) if i.endswith(".pdf")]
    data = {"total": len(files), "skipped": start_index - 1}
    logger.info(f"Started Parsing: {data}")
    for index, fn in enumerate(sorted(files, key=lambda x: int(re.search(r'^\d+', x).group())), 1):
        if index >= start_index:
            fp = pathlib.Path(root_dir).joinpath(fn)
            logger.info(f'[{index} / {len(files)}] parsing {fp.as_uri()}')
            ensure_table(fp)
            time.sleep(0.1)
