"""
日誌管理工具模組

提供統一的日誌配置和管理功能
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logger(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    rotation: str = "1 day",
    retention: str = "30 days",
    format_string: Optional[str] = None
) -> None:
    """
    設定日誌系統
    
    Args:
        log_file: 日誌檔案路徑
        log_level: 日誌等級
        rotation: 日誌輪轉設定
        retention: 日誌保留時間
        format_string: 日誌格式字串
    """
    # 移除預設的 handler
    logger.remove()
    
    # 預設格式
    if format_string is None:
        format_string = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    
    # 添加控制台輸出
    logger.add(
        sys.stderr,
        format=format_string,
        level=log_level,
        colorize=True
    )
    
    # 添加檔案輸出（如果指定了檔案路徑）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=format_string,
            level=log_level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8"
        )
    
    logger.info(f"日誌系統已初始化，等級: {log_level}")


def get_logger(name: str):
    """
    取得指定名稱的 logger
    
    Args:
        name: logger 名稱
        
    Returns:
        logger 實例
    """
    return logger.bind(name=name)
