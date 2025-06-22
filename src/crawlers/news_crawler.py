"""
新聞爬蟲模組

專門用於爬取東吳大學新聞網站的文章內容
"""

from typing import Dict, Any, List
from loguru import logger

from .base_crawler import BaseCrawler
from ..utils import FileHandler


class NewsCrawler(BaseCrawler):
    """新聞爬蟲"""
    
    def __init__(self, config_manager):
        """
        初始化新聞爬蟲
        
        Args:
            config_manager: 配置管理器
        """
        super().__init__(config_manager)
        
        self.news_url = self.config.get_news_url()
        self.category_url = self.news_url + self.config.get("websites.news.category_url")
        self.max_pages = self.config.get_news_max_pages()
        
        # 資料儲存
        self.news_articles: List[Dict[str, str]] = []
    
    def crawl(self) -> Dict[str, Any]:
        """
        執行新聞爬蟲任務
        
        Returns:
            爬取結果統計
        """
        logger.info(f"開始爬取新聞，最多 {self.max_pages} 頁")
        
        try:
            total_articles = 0
            
            for page in range(1, self.max_pages + 1):
                logger.info(f"爬取第 {page} 頁新聞")
                
                page_articles = self._crawl_news_page(page)
                total_articles += len(page_articles)
                
                logger.info(f"第 {page} 頁完成，找到 {len(page_articles)} 篇文章")
                
                # 如果這一頁沒有文章，可能已經到最後一頁
                if not page_articles:
                    logger.info(f"第 {page} 頁沒有文章，停止爬取")
                    break
            
            # 儲存結果
            self._save_results()
            
            result = {
                "success": True,
                "total_pages": page,
                "total_articles": total_articles
            }
            
            logger.info(f"新聞爬取完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"新聞爬取失敗: {e}")
            return {"success": False, "error": str(e)}
    
    def _crawl_news_page(self, page: int) -> List[Dict[str, str]]:
        """
        爬取單一新聞列表頁面
        
        Args:
            page: 頁面編號
            
        Returns:
            文章資料列表
        """
        try:
            page_url = f"{self.category_url}?page={page}"
            page_soup = self.get_page_content(page_url)
            
            if not page_soup:
                logger.warning(f"無法取得新聞列表頁面: {page_url}")
                return []
            
            # 找到文章連結
            article_links = page_soup.select("tbody a")
            if not article_links:
                logger.warning(f"第 {page} 頁沒有找到文章連結")
                return []
            
            # 提取文章 URL 和標題
            articles_data = []
            for link in article_links:
                article_url = link.get("href")
                article_title = link.text.strip()
                
                if article_url and article_title:
                    # 清理標題（移除多餘空白）
                    clean_title = " ".join(article_title.split())
                    
                    articles_data.append({
                        "url": article_url,
                        "title": clean_title
                    })
            
            # 爬取每篇文章的內容
            page_articles = []
            for article_data in articles_data:
                article_content = self._crawl_article_content(
                    article_data["url"], 
                    article_data["title"]
                )
                
                if article_content:
                    page_articles.append(article_content)
            
            return page_articles
            
        except Exception as e:
            logger.error(f"爬取新聞頁面失敗 (第 {page} 頁): {e}")
            return []
    
    def _crawl_article_content(self, article_url: str, title: str) -> Dict[str, str]:
        """
        爬取單篇文章的內容
        
        Args:
            article_url: 文章 URL
            title: 文章標題
            
        Returns:
            文章資料字典
        """
        try:
            article_soup = self.get_page_content(article_url)
            if not article_soup:
                logger.warning(f"無法取得文章內容: {article_url}")
                return None
            
            # 提取文章內容段落
            content_nodes = article_soup.select("#article_block p")
            if not content_nodes:
                logger.warning(f"文章沒有內容段落: {article_url}")
                return None
            
            # 合併所有段落
            content_texts = [node.text.strip() for node in content_nodes if node.text.strip()]
            combined_content = "".join(content_texts)
            
            if not combined_content:
                logger.warning(f"文章內容為空: {article_url}")
                return None
            
            article_data = {
                "url": article_url,
                "title": title,
                "content": combined_content,
                "timestamp": self._get_timestamp()
            }
            
            self.news_articles.append(article_data)
            logger.debug(f"成功爬取文章: {title}")
            
            return article_data
            
        except Exception as e:
            logger.error(f"爬取文章內容失敗 {article_url}: {e}")
            return None
    
    def _save_results(self) -> None:
        """儲存爬取結果到檔案"""
        try:
            # 取得儲存路徑
            data_dirs = self.config.get_data_directories()
            file_names = self.config.get_file_names()
            
            raw_data_dir = data_dirs["raw"]
            
            # 儲存為文字檔案（原始格式）
            news_text_file = f"{raw_data_dir}/{file_names['news_texts']}"
            self._save_as_text_file(news_text_file)
            
            # 儲存為 JSON 檔案（結構化格式）
            news_json_file = f"{raw_data_dir}/{file_names['news_data']}"
            news_data = {
                "articles": self.news_articles,
                "total_count": len(self.news_articles),
                "crawl_timestamp": self._get_timestamp()
            }
            FileHandler.save_json_file(news_json_file, news_data)
            
            logger.info(f"已儲存 {len(self.news_articles)} 篇新聞到 {news_text_file}")
            logger.info(f"已儲存結構化資料到 {news_json_file}")
            
        except Exception as e:
            logger.error(f"儲存新聞結果失敗: {e}")
    
    def _save_as_text_file(self, file_path: str) -> None:
        """
        將新聞儲存為文字檔案格式
        
        Args:
            file_path: 檔案路徑
        """
        try:
            content_lines = []
            
            for article in self.news_articles:
                content_lines.append(f"URL: {article['url']}")
                content_lines.append(f"Title: {article['title']}")
                content_lines.append(article['content'])
                content_lines.append("=" * 80)
            
            content = "\n".join(content_lines)
            FileHandler.save_text_file(file_path, content)
            
        except Exception as e:
            logger.error(f"儲存文字檔案失敗: {e}")
    
    def _get_timestamp(self) -> str:
        """取得當前時間戳記"""
        from datetime import datetime
        return datetime.now().isoformat()
