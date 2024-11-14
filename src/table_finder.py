from typing import Optional, Tuple
from loguru import logger
from .pdf_parser import TableInfo, extract_tables

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
        
    summary = {
        "页码范围": table.page_numbers,
        "是否跨页": table.is_spanning,
        "表格位置": {
            "左上角": (round(table.bbox[0], 2), round(table.bbox[1], 2)),
            "右下角": (round(table.bbox[2], 2), round(table.bbox[3], 2))
        },
        "行数": len(table.content),
        "列数": len(table.content[0]) if table.content else 0,
        "表头": table.content[0] if table.content else [],
    }
    
    # 如果存在置信度属性，则添加到摘要中
    if hasattr(table, 'confidence'):
        summary["置信度"] = round(table.confidence, 3)
        
    return summary

