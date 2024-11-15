from prettytable import PrettyTable
import pandas as pd


def pretty_df(df, merge_cols=None, align='l', float_format='.2f'):
    """
    DataFrame 转 PrettyTable，支持合并单元格

    参数：
        df: pandas DataFrame
        merge_cols: 需要合并的列名列表，如 ['Category']
        align: 对齐方式 'l'=左对齐，'r'=右对齐，'c'=居中
        float_format: 浮点数格式化字符串
    """
    # 创建 PrettyTable 对象
    pt = PrettyTable()

    # 设置表头
    pt.field_names = df.columns.tolist()

    # 设置对齐方式
    for col in df.columns:
        pt.align[col] = align

    # 格式化并添加数据
    for _, row in df.iterrows():
        # 格式化数据
        formatted_row = []
        for col, val in row.items():
            if isinstance(val, float):
                formatted_row.append(format(val, float_format))
            else:
                formatted_row.append(str(val))
        pt.add_row(formatted_row)

    # 处理合并单元格
    if merge_cols:
        for col in merge_cols:
            last_val = None
            for row in pt._rows:
                idx = df.columns.get_loc(col)
                if row[idx] == last_val:
                    row[idx] = ''
                else:
                    last_val = row[idx]

    return pt

#
# # 使用示例
# df = pd.DataFrame({
#     'Category': ['Fruit', 'Fruit', 'Vegetable', 'Vegetable'],
#     'Name': ['Apple', 'Orange', 'Carrot', 'Celery'],
#     'Price': [1.2, 0.9, 0.6, 0.7]
# })
#
# # 基础使用
# print(pretty_df(df))
#
# # 合并 Category 列
# print(pretty_df(df, merge_cols=['Category']))
#
# # 居中对齐，保留一位小数
# print(pretty_df(df,
#                 merge_cols=['Category'],
#                 align='c',
#                 float_format='.1f'))
#
# # 可以设置更多 PrettyTable 的属性
# table = pretty_df(df, merge_cols=['Category'])
# table.border = True
# table.padding_width = 2
# print(table)