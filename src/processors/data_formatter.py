"""
資料格式化模組

提供資料格式轉換和標準化功能
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger

from ..utils import FileHandler


class DataFormatter:
    """資料格式化器"""
    
    def __init__(self, config_manager=None):
        """
        初始化資料格式化器
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
    
    def format_personnel_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化人事資料
        
        Args:
            raw_data: 原始人事資料
            
        Returns:
            格式化後的資料
        """
        try:
            formatted_data = {
                "metadata": {
                    "source": "personnel",
                    "crawl_timestamp": raw_data.get("crawl_timestamp"),
                    "total_documents": raw_data.get("total_documents", 0),
                    "format_timestamp": datetime.now().isoformat()
                },
                "categories": [],
                "documents": []
            }
            
            categories_data = raw_data.get("categories", {})
            doc_id = 1
            
            for category_name, documents in categories_data.items():
                category_info = {
                    "name": category_name,
                    "document_count": len(documents),
                    "document_ids": []
                }
                
                for doc_url in documents:
                    doc_info = {
                        "id": doc_id,
                        "title": category_name,
                        "url": doc_url,
                        "category": category_name,
                        "type": self._detect_document_type(doc_url),
                        "source": "personnel"
                    }
                    
                    formatted_data["documents"].append(doc_info)
                    category_info["document_ids"].append(doc_id)
                    doc_id += 1
                
                formatted_data["categories"].append(category_info)
            
            logger.info(f"人事資料格式化完成: {len(formatted_data['documents'])} 個文件")
            return formatted_data
            
        except Exception as e:
            logger.error(f"人事資料格式化失敗: {e}")
            return {}
    
    def format_news_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化新聞資料
        
        Args:
            raw_data: 原始新聞資料
            
        Returns:
            格式化後的資料
        """
        try:
            articles = raw_data.get("articles", [])
            
            formatted_data = {
                "metadata": {
                    "source": "news",
                    "crawl_timestamp": raw_data.get("crawl_timestamp"),
                    "total_articles": len(articles),
                    "format_timestamp": datetime.now().isoformat()
                },
                "articles": []
            }
            
            for i, article in enumerate(articles, 1):
                formatted_article = {
                    "id": i,
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "content": article.get("content", ""),
                    "publish_timestamp": article.get("timestamp"),
                    "source": "news",
                    "type": "article",
                    "word_count": len(article.get("content", "")),
                    "char_count": len(article.get("content", ""))
                }
                
                formatted_data["articles"].append(formatted_article)
            
            logger.info(f"新聞資料格式化完成: {len(formatted_data['articles'])} 篇文章")
            return formatted_data
            
        except Exception as e:
            logger.error(f"新聞資料格式化失敗: {e}")
            return {}
    
    def merge_datasets(
        self, 
        personnel_data: Dict[str, Any], 
        news_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合併人事資料和新聞資料
        
        Args:
            personnel_data: 格式化後的人事資料
            news_data: 格式化後的新聞資料
            
        Returns:
            合併後的資料集
        """
        try:
            merged_data = {
                "metadata": {
                    "sources": ["personnel", "news"],
                    "merge_timestamp": datetime.now().isoformat(),
                    "total_documents": 0,
                    "personnel_documents": len(personnel_data.get("documents", [])),
                    "news_articles": len(news_data.get("articles", []))
                },
                "documents": []
            }
            
            # 添加人事文件
            for doc in personnel_data.get("documents", []):
                merged_doc = {
                    "id": f"personnel_{doc['id']}",
                    "title": doc["title"],
                    "content": "",  # 人事文件通常是 PDF，沒有文字內容
                    "url": doc["url"],
                    "source": "personnel",
                    "category": doc["category"],
                    "type": doc["type"]
                }
                merged_data["documents"].append(merged_doc)
            
            # 添加新聞文章
            for article in news_data.get("articles", []):
                merged_doc = {
                    "id": f"news_{article['id']}",
                    "title": article["title"],
                    "content": article["content"],
                    "url": article["url"],
                    "source": "news",
                    "category": "新聞",
                    "type": "article",
                    "publish_timestamp": article.get("publish_timestamp")
                }
                merged_data["documents"].append(merged_doc)
            
            merged_data["metadata"]["total_documents"] = len(merged_data["documents"])
            
            logger.info(f"資料集合併完成: {merged_data['metadata']['total_documents']} 個文件")
            return merged_data
            
        except Exception as e:
            logger.error(f"資料集合併失敗: {e}")
            return {}
    
    def export_to_formats(
        self, 
        data: Dict[str, Any], 
        output_dir: str,
        formats: List[str] = None
    ) -> Dict[str, str]:
        """
        將資料匯出為多種格式
        
        Args:
            data: 要匯出的資料
            output_dir: 輸出目錄
            formats: 要匯出的格式列表 ['json', 'csv', 'txt']
            
        Returns:
            匯出檔案路徑字典
        """
        if formats is None:
            formats = ['json', 'csv', 'txt']
        
        output_files = {}
        
        try:
            FileHandler.ensure_directory(output_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # JSON 格式
            if 'json' in formats:
                json_file = f"{output_dir}/scu_data_{timestamp}.json"
                if FileHandler.save_json_file(json_file, data):
                    output_files['json'] = json_file
            
            # CSV 格式（僅文件列表）
            if 'csv' in formats:
                csv_file = f"{output_dir}/scu_data_{timestamp}.csv"
                if self._export_to_csv(data, csv_file):
                    output_files['csv'] = csv_file
            
            # 純文字格式
            if 'txt' in formats:
                txt_file = f"{output_dir}/scu_data_{timestamp}.txt"
                if self._export_to_txt(data, txt_file):
                    output_files['txt'] = txt_file
            
            logger.info(f"資料匯出完成: {list(output_files.keys())}")
            return output_files
            
        except Exception as e:
            logger.error(f"資料匯出失敗: {e}")
            return {}
    
    def _detect_document_type(self, url: str) -> str:
        """
        根據 URL 檢測文件類型
        
        Args:
            url: 文件 URL
            
        Returns:
            文件類型
        """
        url_lower = url.lower()
        
        if url_lower.endswith('.pdf'):
            return 'pdf'
        elif url_lower.endswith(('.doc', '.docx')):
            return 'word'
        elif url_lower.endswith(('.xls', '.xlsx')):
            return 'excel'
        elif url_lower.endswith(('.ppt', '.pptx')):
            return 'powerpoint'
        elif url_lower.endswith('.csv'):
            return 'csv'
        else:
            return 'unknown'
    
    def _export_to_csv(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        匯出為 CSV 格式
        
        Args:
            data: 資料
            file_path: 檔案路徑
            
        Returns:
            是否成功
        """
        try:
            import csv
            
            documents = data.get("documents", [])
            if not documents:
                return False
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'title', 'url', 'source', 'category', 'type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for doc in documents:
                    row = {field: doc.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            logger.error(f"CSV 匯出失敗: {e}")
            return False
    
    def _export_to_txt(self, data: Dict[str, Any], file_path: str) -> bool:
        """
        匯出為純文字格式
        
        Args:
            data: 資料
            file_path: 檔案路徑
            
        Returns:
            是否成功
        """
        try:
            lines = []
            lines.append("東吳大學資料集")
            lines.append("=" * 50)
            lines.append("")
            
            # 元資料
            metadata = data.get("metadata", {})
            lines.append("資料集資訊:")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
            
            # 文件列表
            documents = data.get("documents", [])
            lines.append(f"文件列表 (共 {len(documents)} 個):")
            lines.append("-" * 30)
            
            for doc in documents:
                lines.append(f"ID: {doc.get('id', '')}")
                lines.append(f"標題: {doc.get('title', '')}")
                lines.append(f"來源: {doc.get('source', '')}")
                lines.append(f"類別: {doc.get('category', '')}")
                lines.append(f"URL: {doc.get('url', '')}")
                lines.append("")
            
            content = "\n".join(lines)
            return FileHandler.save_text_file(file_path, content)
            
        except Exception as e:
            logger.error(f"TXT 匯出失敗: {e}")
            return False
