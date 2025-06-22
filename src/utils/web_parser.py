"""
網頁解析工具模組

提供網頁解析相關的工具函數，包括：
- 分頁處理
- 連結提取
- AJAX 請求處理
"""

import re
import json
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import requests
from loguru import logger


class WebParser:
    """網頁解析工具類"""
    
    def __init__(self, session: requests.Session):
        """
        初始化網頁解析器
        
        Args:
            session: requests 會話物件
        """
        self.session = session
    
    def get_max_page(self, soup: BeautifulSoup) -> int:
        """
        從網頁中提取最大頁數
        
        Args:
            soup: BeautifulSoup 解析物件
            
        Returns:
            最大頁數，如果找不到則返回 1
        """
        try:
            # 找到所有帶有 "?page=" 的 a 標籤
            page_links = soup.select("a[href*='?page=']")
            
            # 用正則取出頁碼
            pages = []
            for a in page_links:
                match = re.search(r"[?&]page=(\d+)", a["href"])
                if match:
                    pages.append(int(match.group(1)))
            
            max_page = max(pages) if pages else 1
            logger.info(f"檢測到最大頁數: {max_page}")
            return max_page
            
        except Exception as e:
            logger.warning(f"無法檢測最大頁數: {e}")
            return 1
    
    def extract_href(self, node: BeautifulSoup, base_url: str = "") -> Optional[str]:
        """
        從節點中提取連結
        
        Args:
            node: BeautifulSoup 節點
            base_url: 基礎 URL
            
        Returns:
            完整的 URL 或 None
        """
        try:
            href = node.get("href")
            
            # 處理 JavaScript onclick 事件
            if href == "#":
                onclick = node.get("onclick", "")
                if "location.href=" in onclick:
                    href = onclick.split("location.href=")[1].strip("'\"; ")
            
            # 處理相對路徑
            if href and href.startswith("/"):
                href = base_url + href
                
            return href
            
        except Exception as e:
            logger.warning(f"提取連結失敗: {e}")
            return None
    
    def fetch_ajax_attachments(
        self, 
        node: BeautifulSoup, 
        base_url: str, 
        current_page_url: str,
        title: str,
        doc_extensions: List[str]
    ) -> List[str]:
        """
        處理 AJAX 型的附件請求
        
        Args:
            node: BeautifulSoup 節點
            base_url: 基礎 URL
            current_page_url: 當前頁面 URL
            title: 文件標題
            doc_extensions: 支援的文件副檔名列表
            
        Returns:
            附件 URL 列表
        """
        try:
            data_str = node.get("data-request-data")
            if not data_str:
                logger.warning("缺少 data-request-data 屬性")
                return []
            
            # 解析 data-request-data
            try:
                parts = dict(part.split(":") for part in data_str.split(","))
            except Exception:
                logger.warning(f"無法解析 data-request-data：{data_str}")
                return []
            
            # 準備 AJAX 請求
            headers = {
                "user-agent": self.session.headers.get("user-agent", "Mozilla/5.0"),
                "X-Requested-With": "XMLHttpRequest",
                "X-October-Request-Handler": "web_listcomponent::onAttachmentDetail",
                "Referer": current_page_url,
                "Origin": base_url,
            }
            
            # 發送 POST 請求
            response = self.session.post(current_page_url, headers=headers, data=parts)
            response.raise_for_status()
            
            # 解析回應
            found_attachments = []
            json_response = json.loads(response.text)
            
            if "#rndbox_body" in json_response:
                html_content = json_response["#rndbox_body"]
                soup = BeautifulSoup(html_content, "html.parser")
                
                # 尋找文件連結
                for link in soup.find_all("a", href=True):
                    href = link.get("href")
                    if any(href.lower().endswith(ext) for ext in doc_extensions):
                        full_href = href if href.startswith("http") else base_url + href
                        found_attachments.append(full_href)
                
                if not found_attachments:
                    logger.info(f"文件 '{title}' 沒有找到附件")
            else:
                logger.warning("AJAX 回傳內容中找不到 #rndbox_body 鍵")
                
            return found_attachments
            
        except requests.RequestException as e:
            logger.error(f"AJAX 請求失敗: {e}")
            return []
        except json.JSONDecodeError:
            logger.error("AJAX 回傳內容不是有效的 JSON 格式")
            return []
        except Exception as e:
            logger.error(f"處理 AJAX 附件時發生錯誤: {e}")
            return []
    
    def filter_navigation_links(self, nodes: List[BeautifulSoup]) -> List[BeautifulSoup]:
        """
        過濾掉導航連結，只保留內容連結
        
        Args:
            nodes: BeautifulSoup 節點列表
            
        Returns:
            過濾後的節點列表
        """
        navigation_texts = {"2", "»", "«", "‹", "›", "下一頁", "上一頁", "首頁", "末頁"}
        
        filtered = [
            node for node in nodes
            if len(node.text.strip()) > 3 and node.text.strip() not in navigation_texts
        ]
        
        logger.debug(f"過濾前: {len(nodes)} 個連結，過濾後: {len(filtered)} 個連結")
        return filtered
