from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.config import OUTPUT_DIR
from src.log import LogConfig


@dataclass
class PDFProcessingConfig:
    # PDF处理相关配置
    pdf_folder: Path
    output_file: Path
    progress_file: Path = field(default_factory=lambda: OUTPUT_DIR / "progress.csv")
    page_progress_file: Path = field(default_factory=lambda: OUTPUT_DIR / "page_progress.csv")
    max_workers: Optional[int] = None
    max_test_files: Optional[int] = None  # 测试模式下处理的最大文件数
    processing_timeout: int = 300  # 单个文件处理超时时间(秒)


@dataclass
class ModelConfig:
    # 模型相关配置
    model_name: str = 'all-MiniLM-L6-v2'
    device: str = 'cpu'


@dataclass
class TargetConfig:
    # 目标文本和表格相关配置
    table_name: str = "Summary of project findings and ratings"
    table_position_tolerance: int = 50  # 表格位置匹配的容差(像素)
    min_confidence_threshold: float = 0.5  # 最小相似度阈值


@dataclass
class Config:
    pdf: PDFProcessingConfig
    model: ModelConfig = field(default_factory=ModelConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    log: LogConfig = field(default_factory=LogConfig)

    def __str__(self) -> str:
        """返回格式化的配置信息"""
        return f"""
PDF处理配置:
    文件夹路径: {self.pdf.pdf_folder}
    输出文件: {self.pdf.output_file}
    最大并发数: {self.pdf.max_workers or '自动'}
    测试文件数: {self.pdf.max_test_files or '全部'}
    处理超时: {self.pdf.processing_timeout}秒

模型配置:
    模型名称: {self.model.model_name}
    设备: {self.model.device}

目标配置:
    表格名称: {self.target.table_name}
    位置容差: {self.target.table_position_tolerance}像素
    最小相似度: {self.target.min_confidence_threshold}

日志配置:
    控制台级别: {self.log.console_level}
    文件级别: {self.log.file_level}
    日志文件: {self.log.log_file}
    日志轮转: {self.log.rotation}
"""


# 默认配置
DEFAULT_CONFIG = Config(pdf=PDFProcessingConfig(pdf_folder=Path('/Users/mark/Documents/Terminal evaluation report'),
                                                output_file=OUTPUT_DIR / "pdf_processing_results.xlsx"
                                                # 使用OUTPUT_DIR
                                                ))
STATUS_EMOJI = {
    'pending': '⏳',
    'opening': '📂',
    'processing': '🔄',
    'processing_page': '📄',
    'success': '✅',
    'not_found': '❌',
    'parse_error': '⚠️',
    'error': '💔'}
