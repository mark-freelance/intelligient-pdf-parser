from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import fitz
from loguru import logger


@dataclass
class TableInfo:
    """表格信息数据类"""
    page_numbers: List[int]  # 表格所在的页码列表（跨页的情况可能有多个）
    bbox: List[float]  # 表格边界框 [x0, y0, x1, y1]
    content: List[List[Dict]]  # 表格内容，每个单元格包含文本和格式信息
    confidence: float  # 表格检测的置信度
    is_spanning: bool = False  # 是否是跨页表格


def extract_tables(pdf_path: str, page_callback=None, start_page: int = 0) -> List[TableInfo]:
    """
    从PDF中提取所有表格，包括跨页表格

    Args:
        pdf_path: PDF文件路径
        page_callback: 页面处理进度回调函数
        start_page: 开始处理的页面索引

    Returns:
        List[TableInfo]: 表格信息列表
    """
    doc = fitz.open(pdf_path)
    tables = []
    current_spanning_table = None

    try:
        start_page = max(0, min(start_page, len(doc) - 1))

        for page_num in range(start_page, len(doc)):
            try:
                page = doc[page_num]

                if page_callback:
                    page_callback(page_num, len(doc))

                # 获取当前页面的表格
                page_tables = _extract_page_tables(page)

                # 处理跨页表格
                if current_spanning_table:
                    if page_tables and _is_table_continued(current_spanning_table, page_tables):
                        # 合并跨页表格
                        current_spanning_table = _merge_spanning_table(current_spanning_table, page_tables[0], page_num)
                        page_tables = page_tables[1:]  # 移除已合并的表格
                    else:
                        # 当前跨页表格结束
                        tables.append(current_spanning_table)
                        current_spanning_table = None

                # 检查新的跨页表格
                for table in page_tables:
                    if _is_table_spanning_to_next_page(table, page):
                        current_spanning_table = table
                    else:
                        tables.append(table)

            except Exception as e:
                logger.warning(f"处理页面 {page_num} 时发生错误: {str(e)}")
                continue

        # 添加最后一个跨页表格（如果有）
        if current_spanning_table:
            tables.append(current_spanning_table)

        return tables

    except Exception as e:
        logger.error(f"提取表格时发生错误: {str(e)}")
        return []

    finally:
        doc.close()


def _extract_page_tables(page: fitz.Page) -> List[TableInfo]:
    """
    从单个页面提取表格

    Args:
        page: fitz.Page对象

    Returns:
        List[TableInfo]: 页面中的表格列表
    """
    try:
        tables = []
        tab = page.find_tables()

        if tab.tables:
            for idx, table in enumerate(tab.tables):
                try:
                    # 获取表格内容
                    content = []
                    raw_table = table.extract()
                    if not raw_table:
                        continue

                    # 获取表格的所有单元格信息
                    cells_dict = {}
                    for i in range(len(raw_table)):  # 行
                        for j in range(len(raw_table[0])):  # 列
                            try:
                                # 获取单元格的边界框
                                cell = table.cells[i][j]
                                if isinstance(cell, (tuple, list)) and len(cell) >= 4:
                                    # 如果cell是包含4个坐标的元组或列表
                                    cells_dict[(i, j)] = fitz.Rect(cell)
                                elif hasattr(cell, 'rect'):
                                    # 如果cell是具有rect属性的对象
                                    cells_dict[(i, j)] = cell.rect
                                elif hasattr(cell, 'bbox'):
                                    # 如果cell是具有bbox属性的对象
                                    cells_dict[(i, j)] = fitz.Rect(cell.bbox)
                            except Exception:
                                continue

                    for row_idx, row in enumerate(raw_table):
                        cleaned_row = []
                        for col_idx, cell_content in enumerate(row):
                            try:
                                # 确保cell_content是字符串类型
                                if isinstance(cell_content, dict):
                                    cell_text = str(cell_content.get('text', '')).strip()
                                else:
                                    cell_text = str(cell_content).strip() if cell_content is not None else ""

                                # 获取单元格区域和格式信息
                                is_bold = False
                                try:
                                    cell_rect = cells_dict.get((row_idx, col_idx))
                                    if cell_rect:
                                        dict_output = page.get_text("dict", clip=cell_rect)

                                        # 改进的加粗检测逻辑
                                        for block in dict_output.get("blocks", []):
                                            for line in block.get("lines", []):
                                                for span in line.get("spans", []):
                                                    # 检查字体名称中的加粗标识
                                                    font = span.get("font", "").lower()
                                                    flags = span.get("flags", 0)

                                                    # 通过字体名称检测
                                                    if any(bold_mark in font for bold_mark in
                                                           ["bold", "bd", "-b", "black", "heavy"]):
                                                        is_bold = True
                                                        break

                                                    # 通过字体flags检测 (16是加粗标志)
                                                    if flags & 16:
                                                        is_bold = True
                                                        break

                                                    # 通过字体粗细检测
                                                    weight = span.get("weight", 0)
                                                    if weight >= 600:  # 600及以上通常表示加粗
                                                        is_bold = True
                                                        break

                                                if is_bold:
                                                    break
                                            if is_bold:
                                                break

                                except Exception as e:
                                    logger.debug(f"获取单元格格式信息失败: {str(e)}")

                                # 存储单元格信息
                                cleaned_row.append({'text': cell_text, 'is_bold': is_bold})

                            except Exception as e:
                                logger.debug(f"处理单元格内容失败: {str(e)}")
                                cleaned_row.append({'text': '', 'is_bold': False})

                        content.append(cleaned_row)

                    if content:  # 只有当内容不为空时才创建TableInfo
                        table_info = TableInfo(page_numbers=[page.number],
                                               bbox=list(table.bbox),
                                               content=content,
                                               confidence=1.0,
                                               is_spanning=False)
                        tables.append(table_info)

                except Exception as e:
                    logger.warning(f"处理表格 {idx} 时发生错误: {str(e)}")
                    continue

        return tables

    except Exception as e:
        logger.error(f"处理页面 {page.number} 的表格时发生错误: {str(e)}")
        return []


def _is_table_spanning_to_next_page(table: TableInfo, page: fitz.Page) -> bool:
    """
    判断表格是否跨页
    """
    return True


def _is_table_continued(prev_table: TableInfo, current_page_tables: List[TableInfo]) -> bool:
    """
    判断当前页面的第一个表格是否是上一个表格的继续
    """
    if not current_page_tables:
        return False

    current_table = current_page_tables[0]

    # 检查表格结构是否相似
    prev_cols = len(prev_table.content[0]) if prev_table.content else 0
    curr_cols = len(current_table.content[0]) if current_table.content else 0

    # 列数相同且表格在页面顶部附近
    return prev_cols == curr_cols  # and current_table.bbox[1] < 100


def _merge_spanning_table(
    prev_table: TableInfo, curr_table: TableInfo, current_page: int
) -> TableInfo:
    """
    合并跨页表格
    """
    # 合并页码
    merged_pages = prev_table.page_numbers + [current_page]

    # 合并内容（去除可能的重复表头）
    merged_content = prev_table.content
    curr_content = curr_table.content

    # 如果当前表格的第一行与上一个表格的最后一行相似，可能是重复的表头
    if _is_header_row(curr_content[0], prev_table.content[0]):
        curr_content = curr_content[1:]

    merged_content.extend(curr_content)

    # 创建新的TableInfo
    return TableInfo(page_numbers=merged_pages,
                     bbox=prev_table.bbox,
                     # 保留原始表格的边界框
                     content=merged_content,
                     confidence=min(prev_table.confidence, curr_table.confidence),
                     is_spanning=True)


def _is_header_row(row1: List[Dict], row2: List[Dict]) -> bool:
    """
    判断两行是否是相同的表头
    """
    if len(row1) != len(row2):
        return False

    # 计算相似度（使用文本内容比较）
    similarity = sum(1 for a, b in zip(row1, row2) if a['text'].strip().lower() == b['text'].strip().lower())
    return similarity / len(row1) > 0.8


def find_first_table(pdf_path: str, start_page: int = 0) -> Tuple[Optional[TableInfo], int]:
    """
    从指定页面开始查找第一个表格（包含跨页表格）

    Args:
        pdf_path: PDF文件路径
        start_page: 开始查找的页面索引（从0开始）

    Returns:
        Tuple[Optional[TableInfo], int]:
            - 找到的表格信息（如果没找到则为None）
            - 实际找到表格的起始页码（如果没找到则为-1）
    """
    try:
        # 提取所有表格
        tables = extract_tables(pdf_path, start_page=start_page)

        if not tables:
            logger.info(f"从第 {start_page} 页开始未找到任何表格")
            return None, -1

        # 找到第一个表格（按页码排序）
        first_table = min(tables, key=lambda t: min(t.page_numbers))
        actual_start_page = min(first_table.page_numbers)

        logger.info(f"在第 {actual_start_page} 页找到第一个表格，"
                    f"跨页: {first_table.is_spanning}, "
                    f"页码范围: {first_table.page_numbers}")

        return first_table, actual_start_page

    except Exception as e:
        logger.error(f"查找第一个表格时发生错误: {str(e)}")
        return None, -1


def get_table_summary(table: TableInfo) -> dict:
    """
    获取表格的摘要信息

    Args:
        table: TableInfo对象

    Returns:
        dict: 包含表格关键信息的字典
    """
    if not table:
        return {}

    # 提取表头文本
    header_texts = [cell['text'] for cell in table.content[0]] if table.content else []

    summary = {
        "页码范围": table.page_numbers,
        "是否跨页": table.is_spanning,
        "表格位置": {
            "左上角": (round(table.bbox[0], 2), round(table.bbox[1], 2)),
            "右下角": (round(table.bbox[2], 2), round(table.bbox[3], 2))},
        "行数": len(table.content),
        "列数": len(table.content[0]) if table.content else 0,
        "表头": header_texts, }

    # 如果存在置信度属性，则添加到摘要中
    if hasattr(table, 'confidence'):
        summary["置信度"] = round(table.confidence, 3)

    return summary
