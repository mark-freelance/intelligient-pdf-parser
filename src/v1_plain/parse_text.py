from typing import Dict, Optional

import fitz
from loguru import logger
from sklearn.metrics.pairwise import cosine_similarity

from .config import DEFAULT_CONFIG as config
from .model_loader import ModelLoader

# 获取模型和目标文本
model = ModelLoader.get_model()
target_text = config.target.table_name
target_embedding = model.encode([target_text])


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
            if current_match and (not best_match or current_match['confidence'] > best_match['confidence']):
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

        # 使用滑动窗口在页面中查找最佳匹配
        window_size = len(target_text) * 3  # 使用3倍目标文本长度为窗口大小
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
                    'context_after': context_after}
                max_confidence = confidence

        # 使用正确的配置属性名称：min_confidence_threshold
        if best_match and best_match['confidence'] >= config.target.min_confidence_threshold:
            return best_match

        return None

    except Exception as e:
        logger.error(f"处理页面时发生错误: {str(e)}")
        return None
