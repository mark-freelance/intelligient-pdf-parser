import pathlib

import pymupdf
import pandas as pd
from loguru import logger

from config import root_dir


def ensure_table(fn: str, progress_callback=None):
    """
    处理单个PDF文件的页面

    Args:
        fn: PDF文件名
        progress_callback: 回调函数，用于更新页面处理进度
    """
    fp = pathlib.Path(root_dir).joinpath(fn)
    logger.info(f'parsing file://{fp}')
    doc = pymupdf.open(fp)
    total_pages = len(doc)

    if progress_callback:
        progress_callback(0, total_pages)

    table_data = None
    header = None
    start_page = None
    end_page = None

    for page_idx, page in enumerate(doc, 1):
        logger.debug(f'page {page_idx}')
        if progress_callback:
            progress_callback(page_idx, total_pages)

        try:
            tables = page.find_tables()
        except Exception as e:
            if "not a textpage" in str(e).lower():
                continue
            else:
                raise e

        for table in tables:
            rows = table.to_pandas()
            table_header = table.header.names
            logger.debug(table)

            if 'criterion' in [i.strip().lower() for i in table_header]:
                # print(rows)
                if table_header != header:
                    if header is not None:
                        raise ValueError("发现多个评分表格！每个文档应该只包含一个评分表格。")

                    table_data = rows
                    start_page = page.number
                else:
                    table_data = pd.concat([table_data, rows], axis=0)

                header = table_header
                end_page = page.number

    if table_data is None:
        raise ValueError("未找到评分表格！")
    data = (table_data, start_page, end_page)
    print(data)
    return data


if __name__ == '__main__':
    ensure_table('1.10321_2024_ValTR_unep_gef_msp.pdf')
    ensure_table('3.9142_2024_te_unep_gef_spcmu_lac_Sustainable Cities in Brazil.pdf')
