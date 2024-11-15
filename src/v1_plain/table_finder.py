from typing import List, Tuple

import fitz

from src.v1_plain.format_text import format_text


class TableInfo:
    def __init__(
        self, start_page: int, end_page: int, bbox: Tuple[float, float, float, float], preceding_text: str = ""
        ):
        self.start_page = start_page
        self.end_page = end_page
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.preceding_text = preceding_text
        self.headers = []  # 新增：存储表头信息


class TableFinder:
    def __init__(self, doc_path: str):
        self.doc = fitz.open(doc_path)

    def find_tables_with_context(self) -> List[TableInfo]:
        """查找文档中的所有表格，包括跨页表格，并获取表格前的文本"""
        tables = []
        current_table = None
        table_count = 0
        
        print(f"开始处理PDF文档，总页数: {len(self.doc)}")
        
        for page_num in range(len(self.doc)):
            print(f"\r处理第 {page_num + 1}/{len(self.doc)} 页...", end="", flush=True)
            page = self.doc[page_num]
            table_rects = self._find_table_rectangles(page)
            
            for rect in table_rects:
                if current_table is None:
                    # 发现新表格
                    table_count += 1
                    preceding_text = self._get_preceding_text(page, rect)
                    headers = self._extract_headers(page, rect)
                    current_table = TableInfo(
                        start_page=page_num,
                        end_page=page_num,
                        bbox=rect,
                        preceding_text=preceding_text
                    )
                    current_table.headers = headers
                    
                else:
                    if self._is_continued_table(current_table, page_num, rect):
                        # 更新跨页表格信息
                        current_table.end_page = page_num
                        current_table.bbox = self._merge_bboxes(current_table.bbox, rect)
                    else:
                        # 当前表格结束，输出信息并开始新表格
                        self._print_table_info(current_table, len(tables) + 1)
                        tables.append(current_table)
                        
                        # 开始新表格
                        table_count += 1
                        preceding_text = self._get_preceding_text(page, rect)
                        headers = self._extract_headers(page, rect)
                        current_table = TableInfo(
                            start_page=page_num,
                            end_page=page_num,
                            bbox=rect,
                            preceding_text=preceding_text
                        )
                        current_table.headers = headers

                if not table_rects and current_table is not None:
                    # 当前页没有表格，且存在未完成的表格，输出并保存
                    self._print_table_info(current_table, len(tables) + 1)
                    tables.append(current_table)
                    current_table = None

            if current_table is not None and not self._has_next_page_table(page_num):
                # 如果当前表格不会继续到下一页，输出并保存
                self._print_table_info(current_table, len(tables) + 1)
                tables.append(current_table)
                current_table = None

        # 处理最后一个表格
        if current_table is not None:
            self._print_table_info(current_table, len(tables) + 1)
            tables.append(current_table)

        print(f"\n\n处理完成，共找到 {len(tables)} 个表格。")
        return tables

    def _get_preceding_text(self, page: fitz.Page, table_rect: tuple) -> str:
        """获取表格上方最近的一行文本"""
        # 扩大搜索范围，获取表格上方50-100像素范围内的文本块
        search_rect = (
            table_rect[0] - 20,  # 左边界稍微扩大
            table_rect[1] - 100,  # 上边界扩大到100像素
            table_rect[2] + 20,  # 右边界稍微扩大
            table_rect[1]  # 到表格顶部
        )
        
        blocks = page.get_text("blocks", clip=search_rect)
        if not blocks:
            return ""
        
        # 查找包含"Table"的文本块
        table_blocks = [b for b in blocks if "Table" in b[4]]
        if table_blocks:
            # 返回找到的表格标题
            return table_blocks[0][4].strip()
        
        # 如果没找到包含"Table"的文本，返回最接近表格的文本块
        closest_block = max(blocks, key=lambda b: b[3])
        return closest_block[4].strip()

    def _find_table_rectangles(self, page: fitz.Page) -> List[tuple]:
        """在页面中查找表格"""
        # 配置表格检测参数
        tab = page.find_tables(
            vertical_strategy="text",  # 使用文本定位垂直线
            horizontal_strategy="text",  # 使用文本定位水平线
            intersection_tolerance=3,  # 交叉点容差
            snap_tolerance=3,  # 对齐容差
            join_tolerance=3,  # 连接容差
            edge_min_length=3,  # 最小边长
            min_words_vertical=3,  # 垂直方向最少词数
            min_words_horizontal=1,  # 水平方向最少词数
        )
        
        tables = []
        if tab.tables:
            for table in tab.tables:
                tables.append(table.bbox)
        
        return tables

    def _is_continued_table(
        self, current_table: TableInfo, current_page: int, current_rect: tuple
        ) -> bool:
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
        return (min(bbox1[0], bbox2[0]),  # x0
                bbox1[1],  # 保持原始y0
                max(bbox1[2], bbox2[2]),  # x1
                bbox2[3]  # 使用新的y1
        )

    def _extract_headers(self, page: fitz.Page, table_rect: tuple) -> List[str]:
        """提取表格的表头信息"""
        # 定义表头区域（表格顶部的一小部分区域）
        header_rect = (
            table_rect[0],  # x0
            table_rect[1],  # y0
            table_rect[2],  # x1
            table_rect[1] + 50  # y1: 表格顶部50像素范围
        )
        
        # 获取表头区域的文本块
        blocks = page.get_text("blocks", clip=header_rect)
        if not blocks:
            return []
        
        # 提取并清理表头文本
        headers = []
        for block in blocks:
            header_text = block[4].strip()
            # 过滤掉表格标题（通常包含"Table"字样）
            if header_text and "Table" not in header_text:
                # 如果文本中包含多个列名（用空格分隔），则分别添加
                column_names = [name.strip() for name in header_text.split('  ') if name.strip()]
                headers.extend(column_names)
        
        # 移除重复的表头
        headers = list(dict.fromkeys(headers))
        
        return headers

    def close(self):
        self.doc.close()

    @staticmethod
    def format_text(text: str) -> str:
        """格式化文本，将换行符转换为\n"""
        if not text:
            return ""
        return text.replace('\r', '').replace('\n', '\\n')

    def _print_table_info(self, table: TableInfo, table_num: int):
        """打印表格信息"""
        print(f"\n\n表格 {table_num}:")
        print(f"页码范围: {table.start_page + 1} - {table.end_page + 1}")
        print(f"坐标: ({table.bbox[0]:.1f}, {table.bbox[1]:.1f}, "
              f"{table.bbox[2]:.1f}, {table.bbox[3]:.1f})")
        print(f"前置文本: {format_text(table.preceding_text)}")
        if table.headers:
            print(f"表头: {', '.join(format_text(header) for header in table.headers)}")

    def _has_next_page_table(self, current_page: int) -> bool:
        """检查下一页是否有表格延续"""
        if current_page + 1 >= len(self.doc):
            return False
        
        next_page = self.doc[current_page + 1]
        table_rects = self._find_table_rectangles(next_page)
        return len(table_rects) > 0
