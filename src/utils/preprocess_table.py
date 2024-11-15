import re
from typing import List

import pandas as pd
from sqlmodel import select

from src.database import get_db
from src.models import Paper
from src.log import logger
from src.utils.dataframe import df2data


def preprocess_array(data: List[List[str]], debug=False) -> List[List[str]]:
    columns = data[0]
    return preprocess_dataframe(pd.DataFrame(data[1:], columns=columns), debug)


def preprocess_dataframe(df: pd.DataFrame, debug=False) -> List[List[str]]:
    """
table 是 pymupdf 中的 table 对象，它的表头里会用 r`Col\d+` 表示辅助列，用于与左边（通常）或者右边（如果左边不是实际列的话）的列合并

因此，如果该列的主体所有单元格都为空，或者为 nan、pd.nan 之类，都是可以直接删除的

但如果有数据，则需要考虑合并的问题

合并的唯一原则是，如果某一个单元格和待合并的单元格都不是空且不一样[1]，则一定不是能合并的列

因此，存在无法决定是往左边合并亦或右边合并的情况，这种情况下，请以友好地格式报个

合并完了之后应该生成一个新的没有 Col\d+ 的表格，转化 pd.DataFrame 格式，并使用 markdown 的 grid 格式进行打印输出，然后返回其 DataFrame

示例输入：
+------------------------------+-------------+--------+------------------------------------------------------------------+--------+----------+--------+
| Col0                         | Criterion   | Col2   | Summary assessment                                               | Col4   | Rating   | Col6   |
+==============================+=============+========+==================================================================+========+==========+========+
| Strategic Relevance          |             |        | Overall rating for Strategic Relevance: Highly Satisfactory      |        | HS       |        |
+------------------------------+-------------+--------+------------------------------------------------------------------+--------+----------+--------+
| 1. Alignment to UNEP MTS,    |             |        | Closely aligned with UNEP MTS and POW at the time it was         |        | HS       |        |
| POW and Strategic Priorities |             |        | designed.                                                        |        |          |        |
+------------------------------+-------------+--------+------------------------------------------------------------------+--------+----------+--------+
| 2. Alignment to UNEP         |             |        | The project was aligned with GEF’s strategic priorities. Its aim |        | HS       |        |
| Donor/GEF/Partner strategic  |             |        | was to provide strategic guidance to GEF                         |        |          |        |
| priorities                   |             |        |                                                                  |        |          |        |
+------------------------------+-------------+--------+------------------------------------------------------------------+--------+----------+--------+

示例输出：
+------------------------------+------------------------------------------------------------------+----------+
| Criterion                    | Summary assessment                                               | Rating   |
+===================================+========+===============================================================+
| Strategic Relevance          | Overall rating for Strategic Relevance: Highly Satisfactory      | HS       |
+------------------------------+------------------------------------------------------------------+----------+
| 1. Alignment to UNEP MTS,    | Closely aligned with UNEP MTS and POW at the time it was         | HS       |
| POW and Strategic Priorities | designed.                                                        |          |
+------------------------------+------------------------------------------------------------------+----------+
| 2. Alignment to UNEP         | The project was aligned with GEF’s strategic priorities. Its aim | HS       |
| Donor/GEF/Partner strategic  | was to provide strategic guidance to GEF                         |          |
| priorities                   |                                                                  |          |
+------------------------------+------------------------------------------------------------------+----------+

[1] 16:33:44 | [40 / 444] parsing file:///Users/mark/Documents/Terminal%20evaluation%20report/46.4909_2023_te_unep-gef_fsp_spcc-Global%20Vehicle%20Initiative%20%28GFEI%29_cover%20updated.pdf


    Preprocess PyMuPDF table by merging auxiliary columns and converting to DataFrame.
    
    Args:
        table: PyMuPDF table object with auxiliary columns marked as Col\d+
        
    Returns:
        pd.DataFrame: Processed table without auxiliary columns
        
    Raises:
        ValueError: If merging direction cannot be determined
    """
    if debug:
        logger.debug(f"Initial table state:\n{df.to_markdown(tablefmt='grid')}")

    # Get initial column names and rename empty columns to avoid KeyError
    cols = df.columns.tolist()
    if debug: logger.debug(f"Initial columns: {cols}")

    # Create a mapping of original empty column names to temporary names
    empty_col_map = {}
    for i, col in enumerate(cols):
        if not str(col).strip():
            temp_name = f"__EMPTY_COL_{i}__"
            empty_col_map[temp_name] = col
            cols[i] = temp_name

    # Rename columns in DataFrame
    df.columns = cols

    # Find auxiliary columns (Col\d+ and our temporary empty columns)
    aux_cols = [col for col in cols if not col or re.match(r'Col\d+', str(col)) or col.startswith('__EMPTY_COL_')]
    if debug: logger.debug(f"Found auxiliary columns: {aux_cols}")

    # First pass: handle the first column if it contains content
    first_col = aux_cols[0] if aux_cols else None
    if first_col:
        first_col_values = df[first_col].fillna('')
        first_col_has_content = not all(str(val).strip() == '' for val in first_col_values)

        if first_col_has_content:
            # Find the first non-empty header to merge with
            for col in df.columns:
                if col not in aux_cols and str(col).strip():
                    df[col] = df[first_col].combine_first(df[col])
                    df = df.drop(columns=[first_col])
                    aux_cols.remove(first_col)
                    break

    # Second pass: handle remaining auxiliary columns
    for aux_col in aux_cols:
        if aux_col not in df.columns:  # Skip if already dropped
            continue

        current_cols = df.columns.tolist()
        aux_idx = current_cols.index(aux_col)

        # Check if auxiliary column has content
        col_values = df[aux_col].fillna('')
        is_empty = all(str(val).strip() == '' for val in col_values)
        if is_empty:
            df = df.drop(columns=[aux_col])
            continue

        # Try to merge with adjacent columns
        left_idx = aux_idx - 1
        right_idx = aux_idx + 1

        can_merge_left = left_idx >= 0
        can_merge_right = right_idx < len(current_cols)

        # Modified merging logic: prefer merging with non-auxiliary columns
        if can_merge_right:
            right_col = current_cols[right_idx]
            if right_col not in aux_cols and str(right_col).strip():
                # New merging logic
                for i in range(len(df)):
                    target_val = df.iloc[i, right_idx]
                    aux_val = df.iloc[i, aux_idx]
                    if isinstance(target_val, pd.Series):
                        target_val = target_val.iloc[0] if not target_val.empty else ''
                    if isinstance(aux_val, pd.Series):
                        aux_val = aux_val.iloc[0] if not aux_val.empty else ''
                    if pd.isna(target_val) or str(target_val).strip() == '':
                        df.iat[i, right_idx] = aux_val
                df = df.drop(columns=[aux_col])
                continue

        if can_merge_left:
            left_col = current_cols[left_idx]
            if left_col not in aux_cols and str(left_col).strip():
                # New merging logic
                for i in range(len(df)):
                    target_val = df.iloc[i, left_idx]
                    aux_val = df.iloc[i, aux_idx]
                    if isinstance(target_val, pd.Series):
                        target_val = target_val.iloc[0] if not target_val.empty else ''
                    if isinstance(aux_val, pd.Series):
                        aux_val = aux_val.iloc[0] if not aux_val.empty else ''
                    if pd.isna(target_val) or str(target_val).strip() == '':
                        df.iat[i, left_idx] = aux_val
                df = df.drop(columns=[aux_col])
                continue

        # If we couldn't merge with non-auxiliary columns, try auxiliary columns
        if can_merge_right:
            right_col = current_cols[right_idx]
            for i in range(len(df)):
                target_val = df.iloc[i, right_idx]
                aux_val = df.iloc[i, aux_idx]
                if isinstance(target_val, pd.Series):
                    target_val = target_val.iloc[0] if not target_val.empty else ''
                if isinstance(aux_val, pd.Series):
                    aux_val = aux_val.iloc[0] if not aux_val.empty else ''
                if pd.isna(target_val) or str(target_val).strip() == '':
                    df.iat[i, right_idx] = aux_val
            df = df.drop(columns=[aux_col])
            continue

        if can_merge_left:
            left_col = current_cols[left_idx]
            for i in range(len(df)):
                target_val = df.iloc[i, left_idx]
                aux_val = df.iloc[i, aux_idx]
                if isinstance(target_val, pd.Series):
                    target_val = target_val.iloc[0] if not target_val.empty else ''
                if isinstance(aux_val, pd.Series):
                    aux_val = aux_val.iloc[0] if not aux_val.empty else ''
                if pd.isna(target_val) or str(target_val).strip() == '':
                    df.iat[i, left_idx] = aux_val
            df = df.drop(columns=[aux_col])
            continue

    # Restore original empty column names if any remain
    final_cols = df.columns.tolist()
    for i, col in enumerate(final_cols):
        if col in empty_col_map:
            final_cols[i] = empty_col_map[col]
    df.columns = final_cols

    if debug:
        logger.debug("\nFinal table state:")
        logger.debug(f"Columns: {df.columns.tolist()}")
        logger.debug("Data:")
        for idx, row in df.iterrows():
            logger.debug(f"Row {idx}: {dict(row)}")

    # Remove empty rows before returning
    df = df.dropna(how='all').reset_index(drop=True)

    # Also remove rows where all values are empty strings after stripping
    df = df[~df.apply(lambda x: x.astype(str).str.strip().eq('').all(), axis=1)].reset_index(drop=True)

    # Convert to list format and return
    # First convert all values to strings to ensure homogeneous data
    df = df.astype(str)

    if debug:
        logger.debug(f"\nFinal data into db:\n{df.to_markdown(tablefmt='grid')}")
    return df2data(df)


if __name__ == '__main__':
    DEBUG = True

    with get_db() as session:
        # 更新没有合表的
        query = select(Paper).where(  # Paper.merged_criterion_table == None &
            Paper.criterion_tables_count is not None, Paper.criterion_tables_count > 0)
        papers = session.scalars(query).all()
        for (index, paper) in enumerate(papers[:]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper}")

            tables = paper.criterion_tables
            # print("tables: ", tables)
            raw_data = tables[0].raw_data
            new_data = preprocess_array(raw_data, debug=DEBUG)
            paper.merged_criterion_table = new_data

            session.add(paper)
            session.commit()
