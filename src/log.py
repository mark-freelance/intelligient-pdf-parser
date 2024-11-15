import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import OUTPUT_DIR


@dataclass
class LogConfig:
    # 日志相关配置
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    log_file: Path = OUTPUT_DIR / f"{datetime.now().isoformat()}.log"  # 使用OUTPUT_DIR
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    console_format: str = "<green>{time:HH:mm:ss}</green> | {message}"
    rotation: str = "5 MB"


log_config = LogConfig()

# 移除默认的 stderr 处理器
logger.remove()

# 添加控制台处理器
logger.add(sys.stderr, level=log_config.console_level, format=log_config.console_format, colorize=True)

# 添加文件处理器
logger.add(str(log_config.log_file),
           level=log_config.file_level,
           format=log_config.log_format,
           rotation=log_config.rotation)
