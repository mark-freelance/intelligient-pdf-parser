def preprocess_pymupdf_table(table):
    """
table 是 pymupdf 中的 table 对象，它的表头里会用 r`Col\d+` 表示辅助列，用于与左边（通常）或者右边（如果左边不是实际列的话）的列合并

因此，如果该列的主体所有单元格都为空，或者为 nan、pd.nan 之类，都是可以直接删除的

但如果有数据，则需要考虑合并的问题

合并的唯一原则是，如果某一个单元格和待合并的单元格都不是空，则一定不是能合并的列

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
    """
    pass