"""
檔案處理工具模組

提供檔案操作相關的工具函數，包括：
- 目錄管理
- 檔案讀寫
- 資料序列化
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from loguru import logger


class FileHandler:
    """檔案處理工具類"""
    
    @staticmethod
    def ensure_directory(directory: Union[str, Path]) -> Path:
        """
        確保目錄存在，如果不存在則建立
        
        Args:
            directory: 目錄路徑
            
        Returns:
            Path 物件
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"確保目錄存在: {dir_path}")
        return dir_path
    
    @staticmethod
    def save_text_file(
        file_path: Union[str, Path], 
        content: str, 
        encoding: str = "utf-8",
        mode: str = "w"
    ) -> bool:
        """
        儲存文字檔案
        
        Args:
            file_path: 檔案路徑
            content: 檔案內容
            encoding: 編碼格式
            mode: 寫入模式 ('w' 或 'a')
            
        Returns:
            是否成功儲存
        """
        try:
            file_path = Path(file_path)
            FileHandler.ensure_directory(file_path.parent)
            
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)
            
            logger.info(f"成功儲存檔案: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"儲存檔案失敗 {file_path}: {e}")
            return False
    
    @staticmethod
    def save_lines_to_file(
        file_path: Union[str, Path], 
        lines: List[str], 
        encoding: str = "utf-8",
        sort_lines: bool = False
    ) -> bool:
        """
        將字串列表儲存為檔案，每行一個項目
        
        Args:
            file_path: 檔案路徑
            lines: 字串列表
            encoding: 編碼格式
            sort_lines: 是否排序
            
        Returns:
            是否成功儲存
        """
        try:
            if sort_lines:
                lines = sorted(lines)
            
            content = "\n".join(lines) + "\n"
            return FileHandler.save_text_file(file_path, content, encoding)
            
        except Exception as e:
            logger.error(f"儲存行列表失敗 {file_path}: {e}")
            return False
    
    @staticmethod
    def save_json_file(
        file_path: Union[str, Path], 
        data: Dict[str, Any], 
        encoding: str = "utf-8",
        indent: int = 2
    ) -> bool:
        """
        儲存 JSON 檔案
        
        Args:
            file_path: 檔案路徑
            data: 要儲存的資料
            encoding: 編碼格式
            indent: 縮排空格數
            
        Returns:
            是否成功儲存
        """
        try:
            file_path = Path(file_path)
            FileHandler.ensure_directory(file_path.parent)
            
            with open(file_path, "w", encoding=encoding) as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            logger.info(f"成功儲存 JSON 檔案: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"儲存 JSON 檔案失敗 {file_path}: {e}")
            return False
    
    @staticmethod
    def load_json_file(
        file_path: Union[str, Path], 
        encoding: str = "utf-8"
    ) -> Optional[Dict[str, Any]]:
        """
        載入 JSON 檔案
        
        Args:
            file_path: 檔案路徑
            encoding: 編碼格式
            
        Returns:
            載入的資料或 None
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"檔案不存在: {file_path}")
                return None
            
            with open(file_path, "r", encoding=encoding) as f:
                data = json.load(f)
            
            logger.debug(f"成功載入 JSON 檔案: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"載入 JSON 檔案失敗 {file_path}: {e}")
            return None
    
    @staticmethod
    def load_text_file(
        file_path: Union[str, Path], 
        encoding: str = "utf-8"
    ) -> Optional[str]:
        """
        載入文字檔案
        
        Args:
            file_path: 檔案路徑
            encoding: 編碼格式
            
        Returns:
            檔案內容或 None
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"檔案不存在: {file_path}")
                return None
            
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            
            logger.debug(f"成功載入文字檔案: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"載入文字檔案失敗 {file_path}: {e}")
            return None
    
    @staticmethod
    def append_to_file(
        file_path: Union[str, Path], 
        content: str, 
        encoding: str = "utf-8"
    ) -> bool:
        """
        追加內容到檔案
        
        Args:
            file_path: 檔案路徑
            content: 要追加的內容
            encoding: 編碼格式
            
        Returns:
            是否成功追加
        """
        return FileHandler.save_text_file(file_path, content, encoding, mode="a")
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """
        取得檔案大小
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            檔案大小（位元組）
        """
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return 0
    
    @staticmethod
    def file_exists(file_path: Union[str, Path]) -> bool:
        """
        檢查檔案是否存在
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            檔案是否存在
        """
        return Path(file_path).exists()
