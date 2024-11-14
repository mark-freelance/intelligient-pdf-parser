import fitz
import time
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger
from .model_loader import ModelLoader
from .config import DEFAULT_CONFIG as config
from dataclasses import dataclass
import numpy as np

@dataclass
class TableInfo:
    """表格信息数据类"""
    page_numbers: List[int]  # 表格所在的页码列表（跨页的情况可能有多个）
    bbox: List[float]  # 表格边界框 [x0, y0, x1, y1]
    content: List[List[str]]  # 表格内容，二维数组
    confidence: float  # 表格检测的置信度
    is_spanning: bool = False  # 是否是跨页表格

def find_summary_text(pdf_path: str, page_callback=None, start_page=0) -> Optional[Dict]:
    """
    查找PDF中的目标文本，支持从指定页面开始处理
    
    Args:
        pdf_path: PDF文件路径
        page_callback: 页面处理进度回调函数
        start_page: 开始处理的页面索引（从0开始）
    """
    doc = fitz.open(pdf_path)
    best_match = None
    
    try:
        # 确保 start_page 在有效范围内
        start_page = max(0, min(start_page, len(doc) - 1))
        
        for page_num in range(start_page, len(doc)):
            # 处理每一页...
            if page_callback:
                page_callback(page_num, len(doc), best_match)
                
            # 如果找到更好的匹配，更新 best_match
            current_match = process_page(doc[page_num])  # 假设这是处理单页的函数
            if current_match and (not best_match or 
                current_match['confidence'] > best_match['confidence']):
                best_match = current_match
                
        return best_match
    finally:
        doc.close()
    
def process_page(page) -> Optional[Dict]:
    """
    处理单个PDF页面，查找目标文本
    
    Args:
        page: fitz.Page对象
        
    Returns:
        Dict: 包含匹配结果的字典，如果没有找到匹配则返回None
    """
    try:
        # 获取页面文本
        text = page.get_text()
        if not text.strip():
            return None
            
        # 获取模型和目标文本
        model = ModelLoader.get_model()
        target_text = config.target.table_name
        
        # 使用滑动窗口在页面中查找最佳匹配
        window_size = len(target_text) * 3  # 使用3倍目标文本长度作为窗口大小
        best_match = None
        max_confidence = 0
        
        # 获取所有文本块
        blocks = page.get_text("blocks")
        
        for block in blocks:
            block_text = block[4]  # block[4]是文本内容
            if not block_text.strip():
                continue
                
            # 计算相似度
            text_embedding = model.encode([block_text])
            target_embedding = model.encode([target_text])
            confidence = float(cosine_similarity(text_embedding, target_embedding)[0][0])
            
            if confidence > max_confidence:
                # 提取上下文
                context_before = block_text[:50]  # 取前50个字符作为上文
                context_after = block_text[-50:]  # 取后50个字符作为下文
                
                best_match = {
                    'page_num': page.number,
                    'matched_text': block_text,
                    'confidence': confidence,
                    'text_bbox': block[:4],  # 文本块的边界框
                    'table_bbox': None,  # 如果需要表格边界框，可以在这里添加
                    'context_before': context_before,
                    'context_after': context_after
                }
                max_confidence = confidence
        
        # 使用正确的配置属性名称：min_confidence_threshold
        if best_match and best_match['confidence'] >= config.target.min_confidence_threshold:
            return best_match
            
        return None
        
    except Exception as e:
        logger.error(f"处理页面时发生错误: {str(e)}")
        return None
    
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
            page = doc[page_num]
            
            if page_callback:
                page_callback(page_num, len(doc))
                
            # 获取当前页面的表格
            page_tables = _extract_page_tables(page)
            
            # 处理跨页表格
            if current_spanning_table:
                if _is_table_continued(current_spanning_table, page_tables):
                    # 合并跨页表格
                    current_spanning_table = _merge_spanning_table(
                        current_spanning_table, 
                        page_tables[0], 
                        page_num
                    )
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
        # 使用PyMuPDF的表格检测
        tables = []
        tab = page.find_tables()
        
        if tab.tables:
            for idx, table in enumerate(tab.tables):
                # 获取表格内容
                content = []
                for row in table.extract():
                    # 清理单元格内容
                    cleaned_row = [
                        cell.strip() if isinstance(cell, str) else str(cell)
                        for cell in row
                    ]
                    content.append(cleaned_row)
                
                # 创建TableInfo对象，设置默认confidence为1.0
                table_info = TableInfo(
                    page_numbers=[page.number],
                    bbox=list(table.bbox),  # 转换为list以便序列化
                    content=content,
                    confidence=1.0,  # 由于PyMuPDF的Table对象没有confidence属性，设置默认值
                    is_spanning=False  # 初始设置为非跨页
                )
                tables.append(table_info)
        
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
    return prev_cols == curr_cols # and current_table.bbox[1] < 100

def _merge_spanning_table(prev_table: TableInfo, curr_table: TableInfo, 
                         current_page: int) -> TableInfo:
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
    return TableInfo(
        page_numbers=merged_pages,
        bbox=prev_table.bbox,  # 保留原始表格的边界框
        content=merged_content,
        confidence=min(prev_table.confidence, curr_table.confidence),
        is_spanning=True
    )

def _is_header_row(row1: List[str], row2: List[str]) -> bool:
    """
    判断两行是否是相同的表头
    """
    if len(row1) != len(row2):
        return False
    
    # 计算相似度
    similarity = sum(1 for a, b in zip(row1, row2) 
                    if a.strip().lower() == b.strip().lower())
    return similarity / len(row1) > 0.8
    