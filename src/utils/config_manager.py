"""
配置管理工具模組

提供配置檔案管理功能，包括：
- YAML 配置檔案載入
- 環境變數管理
- 配置驗證
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from loguru import logger

# 載入 .env 檔案
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("已載入 .env 檔案")
except ImportError:
    logger.warning("python-dotenv 未安裝，跳過 .env 檔案載入")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置檔案路徑，預設為 config/settings.yaml
        """
        if config_path is None:
            # 從當前檔案位置往上找到專案根目錄
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            config_path = project_root / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self._config = None
        self.load_config()
    
    def load_config(self) -> bool:
        """
        載入配置檔案
        
        Returns:
            是否成功載入
        """
        try:
            if not self.config_path.exists():
                logger.error(f"配置檔案不存在: {self.config_path}")
                return False
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            
            logger.info(f"成功載入配置檔案: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"載入配置檔案失敗: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        取得配置值，支援點號分隔的巢狀鍵
        
        Args:
            key: 配置鍵，例如 'websites.base_url'
            default: 預設值
            
        Returns:
            配置值
        """
        if self._config is None:
            return default
        
        try:
            keys = key.split(".")
            value = self._config
            
            for k in keys:
                value = value[k]
            
            return value
            
        except (KeyError, TypeError):
            logger.debug(f"配置鍵不存在: {key}，使用預設值: {default}")
            return default
    
    def get_website_config(self) -> Dict[str, Any]:
        """取得網站配置"""
        return self.get("websites", {})
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """取得爬蟲配置"""
        return self.get("crawler", {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """取得儲存配置"""
        return self.get("storage", {})
    
    def get_vectorization_config(self) -> Dict[str, Any]:
        """取得向量化配置"""
        return self.get("vectorization", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """取得日誌配置"""
        return self.get("logging", {})
    
    def get_user_agent(self) -> str:
        """取得 User-Agent"""
        return self.get("crawler.headers.user_agent", 
                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    def get_request_delay(self) -> float:
        """取得請求延遲時間"""
        return self.get("crawler.delays.request_delay", 1.0)
    
    def get_max_retries(self) -> int:
        """取得最大重試次數"""
        return self.get("crawler.delays.max_retries", 3)
    
    def get_timeout(self) -> Dict[str, int]:
        """取得超時設定"""
        return self.get("crawler.timeouts", {"connect": 10, "read": 30})
    
    def get_base_url(self) -> str:
        """取得基礎 URL"""
        return self.get("websites.base_url", "https://web-ch.scu.edu.tw")
    
    def get_news_url(self) -> str:
        """取得新聞 URL"""
        return self.get("websites.news_url", "https://news.scu.edu.tw")
    
    def get_personnel_categories(self) -> list:
        """取得人事資料類別"""
        return self.get("websites.personnel.categories", [])
    
    def get_news_max_pages(self) -> int:
        """取得新聞最大頁數"""
        return self.get("websites.news.max_pages", 50)
    
    def get_data_directories(self) -> Dict[str, str]:
        """取得資料目錄配置"""
        storage_config = self.get_storage_config()
        return {
            "raw": storage_config.get("raw_data_dir", "data/raw"),
            "processed": storage_config.get("processed_data_dir", "data/processed"),
            "vector_db": storage_config.get("vector_db_dir", "data/vector_db")
        }
    
    def get_file_names(self) -> Dict[str, str]:
        """取得檔案名稱配置"""
        return self.get("storage.files", {
            "pdf_links": "pdf_links.txt",
            "news_texts": "news_texts.txt",
            "personnel_data": "personnel_data.json",
            "news_data": "news_data.json"
        })
    
    def get_document_extensions(self) -> list:
        """取得支援的文件副檔名"""
        return self.get("document_types.supported_extensions", [
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", 
            ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp", ".rtf"
        ])
    
    def validate_config(self) -> bool:
        """
        驗證配置檔案的完整性
        
        Returns:
            配置是否有效
        """
        required_keys = [
            "websites.base_url",
            "websites.news_url",
            "storage.raw_data_dir",
            "crawler.headers.user_agent"
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"缺少必要配置: {key}")
                return False
        
        logger.info("配置檔案驗證通過")
        return True
