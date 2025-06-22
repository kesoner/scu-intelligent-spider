"""
爬蟲模組

提供各種專門的爬蟲類別，包括：
- 人事資料爬蟲
- 新聞內容爬蟲
- 基礎爬蟲類別
"""

from .base_crawler import BaseCrawler
from .personnel_crawler import PersonnelCrawler
from .news_crawler import NewsCrawler

__all__ = [
    "BaseCrawler",
    "PersonnelCrawler", 
    "NewsCrawler"
]
