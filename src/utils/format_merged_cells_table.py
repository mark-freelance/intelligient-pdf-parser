from typing import List, Any, Optional
import pandas as pd
from tabulate import tabulate
import numpy as np


def format_merged_cells_table(
    df: pd.DataFrame,
    merge_empty: bool = True,
    default_empty_value: str = '',
    tablefmt: str = 'grid'
    ) -> str:
    """
    格式化DataFrame，支持单元格合并显示的表格

    Args:
        df: 输入的DataFrame
        merge_empty: 是否将空值视为可合并单元格
        default_empty_value: 空值的默认显示
        tablefmt: 表格样式，支持grid/simple/pipe等

    Returns:
        str: 格式化后的表格字符串
    """
    # 复制DataFrame避免修改原始数据
    df_display = df.copy()

    # 统一空值的显示
    if merge_empty:
        df_display = df_display.fillna(default_empty_value)
        df_display = df_display.replace('', default_empty_value)

    # 处理合并单元格的显示
    rows, cols = df_display.shape
    for i in range(rows):
        for j in range(cols):
            current_val = str(df_display.iloc[i, j])

            # 检查是否需要合并（与右侧单元格相同）
            if j < cols - 1:
                right_val = str(df_display.iloc[i, j + 1])
                if current_val == right_val:
                    df_display.iloc[i, j + 1] = default_empty_value

            # 检查是否需要合并（与下方单元格相同）
            if i < rows - 1:
                bottom_val = str(df_display.iloc[i + 1, j])
                if current_val == bottom_val:
                    df_display.iloc[i + 1, j] = default_empty_value

            # 检查是否需要合并（与右下角单元格相同）
            if i < rows - 1 and j < cols - 1:
                bottom_right_val = str(df_display.iloc[i + 1, j + 1])
                if current_val == bottom_right_val:
                    df_display.iloc[i + 1, j + 1] = default_empty_value

    # 使用tabulate格式化输出
    return tabulate(df_display,
                    headers='keys',
                    tablefmt=tablefmt,
                    showindex=True)


# 使用示例
if __name__ == "__main__":
    # 创建测试数据
    data = {
        'Category': ['A', 'A', 'B', 'B'],
        'SubCategory': ['X', 'X', 'Y', 'Y'],
        'Value': [1, 2, 3, 3]
    }
    df = pd.DataFrame(data)

    # 打印合并后的表格
    print("原始表格：")
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=True))
    print("\n合并后的表格：")
    print(format_merged_cells_table(df))