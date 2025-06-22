"""
文本處理模組

提供文本清理、分割和預處理功能
"""

import re
from typing import List, Dict, Any, Optional
from loguru import logger


class TextProcessor:
    """文本處理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化文本處理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        
        # 從配置取得文本處理參數
        if config_manager:
            text_config = config_manager.get("vectorization.text_processing", {})
            self.chunk_size = text_config.get("chunk_size", 1000)
            self.chunk_overlap = text_config.get("chunk_overlap", 200)
            self.max_tokens = text_config.get("max_tokens", 8192)
        else:
            self.chunk_size = 1000
            self.chunk_overlap = 200
            self.max_tokens = 8192
    
    def clean_text(self, text: str) -> str:
        """
        清理文本內容
        
        Args:
            text: 原始文本
            
        Returns:
            清理後的文本
        """
        if not text:
            return ""
        
        try:
            # 移除多餘的空白字符
            text = re.sub(r'\s+', ' ', text)
            
            # 移除特殊字符（保留中文、英文、數字和基本標點）
            text = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()[\]{}""''「」『』、。，！？；：（）【】]', '', text)
            
            # 移除連續的標點符號
            text = re.sub(r'[.,!?;:]{2,}', '.', text)
            
            # 去除首尾空白
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.warning(f"文本清理失敗: {e}")
            return text
    
    def split_text_into_chunks(
        self, 
        text: str, 
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None
    ) -> List[str]:
        """
        將長文本分割成較小的塊
        
        Args:
            text: 要分割的文本
            chunk_size: 每塊的大小（字符數）
            overlap: 重疊字符數
            
        Returns:
            文本塊列表
        """
        if not text:
            return []
        
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.chunk_overlap
        
        try:
            # 如果文本長度小於塊大小，直接返回
            if len(text) <= chunk_size:
                return [text]
            
            chunks = []
            start = 0
            
            while start < len(text):
                # 計算結束位置
                end = start + chunk_size
                
                # 如果不是最後一塊，嘗試在句號處分割
                if end < len(text):
                    # 尋找最近的句號
                    last_period = text.rfind('。', start, end)
                    if last_period > start:
                        end = last_period + 1
                
                # 提取文本塊
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # 計算下一個開始位置（考慮重疊）
                start = max(start + 1, end - overlap)
                
                # 避免無限循環
                if start >= len(text):
                    break
            
            logger.debug(f"文本分割完成: {len(text)} 字符 -> {len(chunks)} 塊")
            return chunks
            
        except Exception as e:
            logger.error(f"文本分割失敗: {e}")
            return [text]  # 返回原始文本作為單一塊
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        從文本中提取關鍵詞
        
        Args:
            text: 輸入文本
            max_keywords: 最大關鍵詞數量
            
        Returns:
            關鍵詞列表
        """
        if not text:
            return []
        
        try:
            # 簡單的關鍵詞提取（基於詞頻）
            # 移除標點符號
            clean_text = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', text)
            
            # 分詞（簡單按空格分割）
            words = clean_text.split()
            
            # 過濾短詞和常見詞
            stop_words = {'的', '是', '在', '有', '和', '與', '或', '但', '而', '了', '也', '都', '會', '可以', '可能'}
            filtered_words = [
                word for word in words 
                if len(word) > 1 and word not in stop_words
            ]
            
            # 計算詞頻
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # 按頻率排序並取前 N 個
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, freq in keywords[:max_keywords]]
            
            return keywords
            
        except Exception as e:
            logger.warning(f"關鍵詞提取失敗: {e}")
            return []
    
    def normalize_text(self, text: str) -> str:
        """
        標準化文本格式
        
        Args:
            text: 輸入文本
            
        Returns:
            標準化後的文本
        """
        if not text:
            return ""
        
        try:
            # 轉換為小寫（僅針對英文）
            text = re.sub(r'[A-Z]', lambda m: m.group().lower(), text)
            
            # 統一標點符號
            text = text.replace('，', ',')
            text = text.replace('。', '.')
            text = text.replace('！', '!')
            text = text.replace('？', '?')
            text = text.replace('；', ';')
            text = text.replace('：', ':')
            
            # 移除多餘空格
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.warning(f"文本標準化失敗: {e}")
            return text
    
    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理單個文件
        
        Args:
            document: 文件資料
            
        Returns:
            處理後的文件資料
        """
        try:
            processed_doc = document.copy()
            
            # 清理標題
            if 'title' in document:
                processed_doc['title'] = self.clean_text(document['title'])
            
            # 清理內容
            if 'content' in document:
                content = document['content']
                
                # 清理文本
                clean_content = self.clean_text(content)
                processed_doc['content'] = clean_content
                
                # 分割成塊
                chunks = self.split_text_into_chunks(clean_content)
                processed_doc['chunks'] = chunks
                
                # 提取關鍵詞
                keywords = self.extract_keywords(clean_content)
                processed_doc['keywords'] = keywords
                
                # 計算統計信息
                processed_doc['stats'] = {
                    'char_count': len(clean_content),
                    'chunk_count': len(chunks),
                    'keyword_count': len(keywords)
                }
            
            return processed_doc
            
        except Exception as e:
            logger.error(f"文件處理失敗: {e}")
            return document
