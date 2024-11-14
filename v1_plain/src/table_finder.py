from typing import List, Tuple, Optional
import fitz
import re

class TableInfo:
    def __init__(self, 
                 start_page: int,
                 end_page: int, 
                 bbox: Tuple[float, float, float, float],
                 preceding_text: str = ""):
        self.start_page = start_page
        self.end_page = end_page
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.preceding_text = preceding_text

class TableFinder:
    def __init__(self, doc_path: str):
        self.doc = fitz.open(doc_path)
        
    def find_tables_with_context(self) -> List[TableInfo]:
        """查找文档中的所有表格，包括跨页表格，并获取表格前的文本"""
        tables = []
        current_table = None
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # 查找当前页面的表格边框
            table_rects = self._find_table_rectangles(page)
            
            for rect in table_rects:
                if current_table is None:
                    # 新表格，获取前置文本
                    preceding_text = self._get_preceding_text(page, rect)
                    current_table = TableInfo(
                        start_page=page_num,
                        end_page=page_num,
                        bbox=rect,
                        preceding_text=preceding_text
                    )
                else:
                    # 检查是否是跨页表格的继续
                    if self._is_continued_table(current_table, page_num, rect):
                        current_table.end_page = page_num
                        current_table.bbox = self._merge_bboxes(current_table.bbox, rect)
                    else:
                        # 保存当前表格，开始新表格
                        tables.append(current_table)
                        preceding_text = self._get_preceding_text(page, rect)
                        current_table = TableInfo(
                            start_page=page_num,
                            end_page=page_num,
                            bbox=rect,
                            preceding_text=preceding_text
                        )
            
            # 如果当前页没有找到表格，且存在未完成的表格，则保存它
            if not table_rects and current_table is not None:
                tables.append(current_table)
                current_table = None
                
        # 处理最后一个表格
        if current_table is not None:
            tables.append(current_table)
            
        return tables
    
    def _get_preceding_text(self, page: fitz.Page, table_rect: tuple) -> str:
        """获取表格上方最近的一行文本"""
        # 获取表格上方区域的文本块
        blocks = page.get_text("blocks")
        preceding_blocks = [b for b in blocks if b[3] < table_rect[1]]  # y1 < table's y0
        
        if not preceding_blocks:
            return ""
            
        # 获取最接近表格的文本块
        closest_block = max(preceding_blocks, key=lambda b: b[3])
        return closest_block[4].strip()
    
    def _find_table_rectangles(self, page: fitz.Page) -> List[tuple]:
        """在页面中查找可能的表格边框"""
        # 获取页面中的所有矩形
        rects = []
        for drawing in page.get_drawings():
            if drawing["type"] == "rect":
                rect = drawing["rect"]
                # 过滤掉太小的矩形
                if (rect[2] - rect[0]) > 100 and (rect[3] - rect[1]) > 50:
                    rects.append(rect)
        return rects
    
    def _is_continued_table(self, 
                           current_table: TableInfo, 
                           current_page: int,
                           current_rect: tuple) -> bool:
        """判断当前矩形是否是跨页表格的继续"""
        # 如果不是连续页面，则不是跨页表格
        if current_page != current_table.end_page + 1:
            return False
            
        # 检查横向位置和宽度是否相似
        prev_width = current_table.bbox[2] - current_table.bbox[0]
        curr_width = current_rect[2] - current_rect[0]
        x_diff = abs(current_table.bbox[0] - current_rect[0])
        
        return (abs(prev_width - curr_width) < 20 and x_diff < 20)
    
    def _merge_bboxes(self, bbox1: tuple, bbox2: tuple) -> tuple:
        """合并两个边界框"""
        return (
            min(bbox1[0], bbox2[0]),  # x0
            bbox1[1],                 # 保持原始y0
            max(bbox1[2], bbox2[2]),  # x1
            bbox2[3]                  # 使用新的y1
        )
    
    def close(self):
        self.doc.close() 