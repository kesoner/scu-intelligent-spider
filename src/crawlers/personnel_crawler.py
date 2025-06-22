"""
人事資料爬蟲模組

專門用於爬取東吳大學人事室的各類公告文件
"""

from typing import Dict, Any, List, Set
from collections import defaultdict
from loguru import logger

from .base_crawler import BaseCrawler
from ..utils import FileHandler


class PersonnelCrawler(BaseCrawler):
    """人事資料爬蟲"""
    
    def __init__(self, config_manager):
        """
        初始化人事資料爬蟲
        
        Args:
            config_manager: 配置管理器
        """
        super().__init__(config_manager)
        
        self.base_url = self.config.get_base_url()
        self.menu_url = self.base_url + self.config.get("websites.personnel.menu_url")
        self.categories = self.config.get_personnel_categories()
        self.doc_extensions = self.config.get_document_extensions()
        
        # 資料儲存
        self.pdf_links_set: Set[str] = set()
        self.attachments_data: Dict[str, List[str]] = defaultdict(list)
    
    def crawl(self) -> Dict[str, Any]:
        """
        執行人事資料爬蟲任務
        
        Returns:
            爬取結果統計
        """
        logger.info("開始爬取人事資料")
        
        try:
            # 取得主選單頁面
            menu_soup = self.get_page_content(self.menu_url)
            if not menu_soup:
                logger.error("無法取得主選單頁面")
                return {"success": False, "error": "無法取得主選單頁面"}
            
            # 解析類別連結
            category_links = self._parse_category_links(menu_soup)
            if not category_links:
                logger.error("未找到任何類別連結")
                return {"success": False, "error": "未找到任何類別連結"}
            
            # 爬取每個類別
            total_documents = 0
            for title, href in category_links:
                logger.info(f"🔹 處理類別: {title}")
                
                category_count = self._crawl_category(title, href)
                total_documents += category_count
                
                logger.info(f"類別 '{title}' 完成，找到 {category_count} 個文件")
            
            # 儲存結果
            self._save_results()
            
            result = {
                "success": True,
                "total_categories": len(category_links),
                "total_documents": total_documents,
                "unique_pdf_links": len(self.pdf_links_set)
            }
            
            logger.info(f"人事資料爬取完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"人事資料爬取失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_category_links(self, soup) -> List[tuple]:
        """
        解析主選單中的類別連結
        
        Args:
            soup: 主選單頁面的 BeautifulSoup 物件
            
        Returns:
            (標題, 連結) 的列表
        """
        try:
            nodes = soup.select(".group a")
            
            titles = [node.text.strip() for node in nodes]
            hrefs = [node.get("href") for node in nodes]
            
            category_links = list(zip(titles, hrefs))
            logger.info(f"找到 {len(category_links)} 個類別")
            
            return category_links
            
        except Exception as e:
            logger.error(f"解析類別連結失敗: {e}")
            return []
    
    def _crawl_category(self, title: str, href: str) -> int:
        """
        爬取單一類別的所有頁面
        
        Args:
            title: 類別標題
            href: 類別連結
            
        Returns:
            找到的文件數量
        """
        try:
            # 建立完整 URL
            category_url = href if href.startswith("http") else self.base_url + href
            
            # 取得第一頁以確定總頁數
            first_page_soup = self.get_page_content(category_url)
            if not first_page_soup:
                logger.warning(f"無法取得類別頁面: {category_url}")
                return 0

            max_page = self.web_parser.get_max_page(first_page_soup)
            logger.info(f"    類別 '{title}' 總共 {max_page} 頁")

            document_count = 0

            # 爬取每一頁
            for page in range(1, max_page + 1):
                page_url = f"{category_url}?page={page}"
                logger.info(f"    ▶ 抓取第 {page} 頁: {page_url}")

                page_count = self._crawl_page(page_url, title)
                document_count += page_count

            return document_count

        except Exception as e:
            logger.error(f"爬取類別 '{title}' 失敗: {e}")
            return 0

    def _crawl_page(self, page_url: str, category_title: str) -> int:
        """
        爬取單一頁面的文件連結

        Args:
            page_url: 頁面 URL
            category_title: 類別標題

        Returns:
            找到的文件數量
        """
        try:
            page_soup = self.get_page_content(page_url)
            if not page_soup:
                logger.warning(f"無法取得頁面: {page_url}")
                return 0

            # 找到所有連結
            inner_links = page_soup.select("tbody a") or page_soup.select("#rndbox_body a")
            filtered_links = self.web_parser.filter_navigation_links(inner_links)

            document_count = 0

            for node in filtered_links:
                document_title = node.text.strip()

                # 處理 AJAX 請求
                if node.get("data-request") == "web_listcomponent::onAttachmentDetail":
                    urls = self.web_parser.fetch_ajax_attachments(
                        node, self.base_url, page_url, document_title, self.doc_extensions
                    )
                else:
                    # 處理一般連結
                    href = self.web_parser.extract_href(node, self.base_url)
                    urls = [href] if href else []

                # 儲存找到的 URL
                for url in urls:
                    if url and url not in self.attachments_data[document_title]:
                        self.attachments_data[document_title].append(url)
                        self.pdf_links_set.add(url)
                        document_count += 1

                        logger.info(f"        ✅ {document_title}: {url}")

            return document_count

        except Exception as e:
            logger.error(f"爬取頁面失敗 {page_url}: {e}")
            return 0

    def _save_results(self) -> None:
        """儲存爬取結果到檔案"""
        try:
            # 取得儲存路徑
            data_dirs = self.config.get_data_directories()
            file_names = self.config.get_file_names()

            raw_data_dir = data_dirs["raw"]

            # 儲存 PDF 連結列表
            pdf_links_file = f"{raw_data_dir}/{file_names['pdf_links']}"
            FileHandler.save_lines_to_file(
                pdf_links_file,
                list(self.pdf_links_set),
                sort_lines=True
            )

            # 儲存詳細的附件資料
            personnel_data_file = f"{raw_data_dir}/{file_names['personnel_data']}"
            personnel_data = {
                "categories": dict(self.attachments_data),
                "total_documents": len(self.pdf_links_set),
                "crawl_timestamp": self._get_timestamp()
            }
            FileHandler.save_json_file(personnel_data_file, personnel_data)

            logger.info(f"已儲存 {len(self.pdf_links_set)} 筆 PDF 連結到 {pdf_links_file}")
            logger.info(f"已儲存詳細資料到 {personnel_data_file}")

        except Exception as e:
            logger.error(f"儲存結果失敗: {e}")

    def _get_timestamp(self) -> str:
        """取得當前時間戳記"""
        from datetime import datetime
        return datetime.now().isoformat()
