"""
基礎爬蟲類別

提供所有爬蟲的共用功能和介面
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from loguru import logger

from ..utils import ConfigManager, WebParser


class BaseCrawler(ABC):
    """基礎爬蟲抽象類別"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化基礎爬蟲
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.session = self._create_session()
        self.web_parser = WebParser(self.session)
        
        # 從配置取得設定
        self.request_delay = self.config.get_request_delay()
        self.max_retries = self.config.get_max_retries()
        self.timeout = self.config.get_timeout()
        
        logger.info(f"初始化 {self.__class__.__name__}")
    
    def _create_session(self) -> requests.Session:
        """
        建立 requests 會話

        Returns:
            配置好的 requests.Session
        """
        session = requests.Session()

        # 設定 headers
        session.headers.update({
            "user-agent": self.config.get_user_agent()
        })

        # 設定超時（將在請求時使用）
        self.timeout_config = self.config.get_timeout()

        # 處理 SSL 證書問題（開發環境）
        session.verify = False

        # 禁用 SSL 警告
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        return session
    
    def make_request(
        self, 
        url: str, 
        method: str = "GET", 
        **kwargs
    ) -> Optional[requests.Response]:
        """
        發送 HTTP 請求，包含重試機制
        
        Args:
            url: 請求 URL
            method: HTTP 方法
            **kwargs: 其他請求參數
            
        Returns:
            Response 物件或 None
        """
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"請求 {url} (嘗試 {attempt + 1}/{self.max_retries + 1})")
                
                # 設定超時
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = (self.timeout_config["connect"], self.timeout_config["read"])

                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                # 請求成功，添加延遲
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                
                return response
                
            except requests.RequestException as e:
                logger.warning(f"請求失敗 {url}: {e}")
                
                if attempt < self.max_retries:
                    retry_delay = self.config.get("crawler.delays.retry_delay", 5.0)
                    logger.info(f"等待 {retry_delay} 秒後重試...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"請求最終失敗 {url}")
                    return None
    
    def parse_html(self, html_content: str) -> BeautifulSoup:
        """
        解析 HTML 內容
        
        Args:
            html_content: HTML 字串
            
        Returns:
            BeautifulSoup 物件
        """
        return BeautifulSoup(html_content, "html.parser")
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """
        取得頁面內容並解析
        
        Args:
            url: 頁面 URL
            
        Returns:
            BeautifulSoup 物件或 None
        """
        response = self.make_request(url)
        if response:
            return self.parse_html(response.text)
        return None
    
    @abstractmethod
    def crawl(self) -> Dict[str, Any]:
        """
        執行爬蟲任務
        
        Returns:
            爬取結果
        """
        pass
    
    def __enter__(self):
        """上下文管理器進入"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self.session:
            self.session.close()
            logger.debug("已關閉 requests 會話")
