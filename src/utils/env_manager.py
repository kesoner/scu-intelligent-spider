"""
環境變數管理模組

提供環境變數載入和管理功能
"""

import os
from pathlib import Path
from typing import Optional, Union
from dotenv import load_dotenv
from loguru import logger


class EnvManager:
    """環境變數管理器"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        初始化環境變數管理器
        
        Args:
            env_file: .env 檔案路徑，預設為專案根目錄的 .env
        """
        if env_file is None:
            # 從當前檔案位置往上找到專案根目錄
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            env_file = project_root / ".env"
        
        self.env_file = Path(env_file)
        self.load_env()
    
    def load_env(self) -> bool:
        """
        載入環境變數檔案
        
        Returns:
            是否成功載入
        """
        try:
            if self.env_file.exists():
                load_dotenv(self.env_file)
                logger.info(f"成功載入環境變數檔案: {self.env_file}")
                return True
            else:
                logger.warning(f"環境變數檔案不存在: {self.env_file}")
                return False
                
        except Exception as e:
            logger.error(f"載入環境變數檔案失敗: {e}")
            return False
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        取得環境變數值
        
        Args:
            key: 環境變數鍵
            default: 預設值
            
        Returns:
            環境變數值
        """
        return os.getenv(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        取得布林型環境變數
        
        Args:
            key: 環境變數鍵
            default: 預設值
            
        Returns:
            布林值
        """
        value = self.get(key)
        if value is None:
            return default
        
        return value.lower() in ("true", "1", "yes", "on")
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        取得整數型環境變數
        
        Args:
            key: 環境變數鍵
            default: 預設值
            
        Returns:
            整數值
        """
        value = self.get(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except ValueError:
            logger.warning(f"環境變數 {key} 不是有效的整數: {value}")
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        取得浮點數型環境變數
        
        Args:
            key: 環境變數鍵
            default: 預設值
            
        Returns:
            浮點數值
        """
        value = self.get(key)
        if value is None:
            return default
        
        try:
            return float(value)
        except ValueError:
            logger.warning(f"環境變數 {key} 不是有效的浮點數: {value}")
            return default
    
    def set(self, key: str, value: Union[str, int, float, bool]) -> None:
        """
        設定環境變數
        
        Args:
            key: 環境變數鍵
            value: 環境變數值
        """
        os.environ[key] = str(value)
    
    def require(self, key: str) -> str:
        """
        取得必要的環境變數，如果不存在則拋出異常
        
        Args:
            key: 環境變數鍵
            
        Returns:
            環境變數值
            
        Raises:
            ValueError: 如果環境變數不存在
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"必要的環境變數 {key} 未設定")
        return value
    
    def list_all(self) -> dict:
        """
        列出所有環境變數
        
        Returns:
            環境變數字典
        """
        return dict(os.environ)
