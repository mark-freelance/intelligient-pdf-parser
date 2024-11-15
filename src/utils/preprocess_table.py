import pandas
import pymupdf.table

from src.log import logger


def preprocess_pymupdf_table(table: pymupdf.table.Table) -> pandas.DataFrame:
    """
table 是 pymupdf 中的 table 对象，它的表头里会用 r`Col\d+` 表示辅助列，用于与左边（通常）或者右边（如果左边不是实际列的话）的列合并

因此，如果该列的主体所有单元格都为空，或者为 nan、pd.nan 之类，都是可以直接删除的

但如果有数据，则需要考虑合并的问题

合并的唯一原则是，如果某一个单元格和待合并的单元格都不是空且不一样[1]，则一定不是能合并的列

因此，存在无法决定是往左边合并亦或右边合并的情况，这种情况下，请以友好地格式报个错

合并完了之后应该生成一个新的没有 Col\d+ 的表格，转化成 pd.DataFrame 格式，并使用 markdown 的 grid 格式进行打印输出，然后返回其 DataFrame

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
    import pandas as pd
    import re

    # Convert table to DataFrame
    df = table.to_pandas()
    # logger.debug(f"Initial table state:\n{df.to_markdown(index=False, tablefmt='grid')}")

    # Get initial column names
    cols = df.columns.tolist()
    # logger.debug(f"Initial columns: {cols}")

    # Find auxiliary columns (Col\d+)
    aux_cols = [col for col in cols if re.match(r'Col\d+', str(col))]
    # logger.debug(f"Found auxiliary columns: {aux_cols}")

    # Process each auxiliary column
    for aux_col in aux_cols:
        # logger.debug(f"\nProcessing auxiliary column: {aux_col}")
        
        # Skip if column was already dropped in previous iterations
        if aux_col not in df.columns:
            # logger.debug(f"Column {aux_col} was already dropped, skipping")
            continue

        # Find auxiliary column index based on current columns
        current_cols = df.columns.tolist()
        aux_idx = current_cols.index(aux_col)
        # logger.debug(f"Current columns: {current_cols}")

        # Skip if all values in auxiliary column are empty/nan
        if df[aux_col].isna().all() or (df[aux_col] == '').all():
            # logger.debug(f"Column {aux_col} is empty, dropping it")
            df = df.drop(columns=[aux_col])
            # logger.debug(f"Table after dropping empty column:\n{df.to_markdown(index=False, tablefmt='grid')}")
            continue

        # Try to merge with adjacent columns
        left_idx = aux_idx - 1
        right_idx = aux_idx + 1

        can_merge_left = left_idx >= 0
        can_merge_right = right_idx < len(current_cols)
        
        # logger.debug(f"Can merge left: {can_merge_left}, Can merge right: {can_merge_right}")
        if can_merge_left:
            # logger.debug(f"Left column: {current_cols[left_idx]}")
            pass
        if can_merge_right:
            # logger.debug(f"Right column: {current_cols[right_idx]}")
            pass

        # Check if we can merge left
        conflict_left = False
        left_conflicts = []
        if can_merge_left:
            left_col = current_cols[left_idx]
            for i in range(len(df)):
                if pd.notna(df[aux_col].iloc[i]) and pd.notna(df[left_col].iloc[i]) and \
                   df[aux_col].iloc[i] != '' and df[left_col].iloc[i] != '' and \
                   df[aux_col].iloc[i] != df[left_col].iloc[i]:
                    conflict_left = True
                    left_conflicts.append({
                        'row': i,
                        'aux_value': df[aux_col].iloc[i],
                        'left_value': df[left_col].iloc[i]
                    })

        # Check if we can merge right
        conflict_right = False
        right_conflicts = []
        if can_merge_right:
            right_col = current_cols[right_idx]
            for i in range(len(df)):
                if pd.notna(df[aux_col].iloc[i]) and pd.notna(df[right_col].iloc[i]) and \
                   df[aux_col].iloc[i] != '' and df[right_col].iloc[i] != '' and \
                   df[aux_col].iloc[i] != df[right_col].iloc[i]:
                    conflict_right = True
                    right_conflicts.append({
                        'row': i,
                        'aux_value': df[aux_col].iloc[i],
                        'right_value': df[right_col].iloc[i]
                    })

        # Determine merge direction
        if can_merge_left and not conflict_left:
            left_col = current_cols[left_idx]
            # logger.debug(f"Merging column {aux_col} to left with {left_col}")
            # logger.debug("Values to be merged:")
            for i in range(len(df)):
                if pd.notna(df[aux_col].iloc[i]) and df[aux_col].iloc[i] != '':
                    # logger.debug(f"Row {i}: '{df[aux_col].iloc[i]}' -> '{df[left_col].iloc[i]}'")
                    df.loc[i, left_col] = df[aux_col].iloc[i]
            df = df.drop(columns=[aux_col])
            # logger.debug(f"Table after merging left:\n{df.to_markdown(index=False, tablefmt='grid')}")

        elif can_merge_right and not conflict_right:
            right_col = current_cols[right_idx]
            # logger.debug(f"Merging column {aux_col} to right with {right_col}")
            # logger.debug("Values to be merged:")
            for i in range(len(df)):
                if pd.notna(df[aux_col].iloc[i]) and df[aux_col].iloc[i] != '':
                    # logger.debug(f"Row {i}: '{df[aux_col].iloc[i]}' -> '{df[right_col].iloc[i]}'")
                    df.loc[i, right_col] = df[aux_col].iloc[i]
            df = df.drop(columns=[aux_col])
            # logger.debug(f"Table after merging right:\n{df.to_markdown(index=False, tablefmt='grid')}")

        else:
            # Log detailed conflict information
            logger.error(f"\nCannot merge column {aux_col}:")
            logger.error(f"Current table state:\n{df.to_markdown(index=False, tablefmt='grid')}")
            
            if can_merge_left:
                logger.error(f"\nLeft conflicts with {left_col}:")
                for conflict in left_conflicts:
                    logger.error(f"Row {conflict['row']}: aux='{conflict['aux_value']}' left='{conflict['left_value']}'")
            
            if can_merge_right:
                logger.error(f"\nRight conflicts with {right_col}:")
                for conflict in right_conflicts:
                    logger.error(f"Row {conflict['row']}: aux='{conflict['aux_value']}' right='{conflict['right_value']}'")

            raise ValueError(
                f"Cannot determine merge direction for column {aux_col}.\n"
                f"Left mergeable: {can_merge_left} (conflicts: {bool(left_conflicts)})\n"
                f"Right mergeable: {can_merge_right} (conflicts: {bool(right_conflicts)})"
            )

    # logger.debug(f"\nFinal table state:\n{df.to_markdown(index=False, tablefmt='grid')}")
    return df
