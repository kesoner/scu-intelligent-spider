"""
向量處理模組

提供文件向量化和搜尋功能
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger

try:
    from llama_index.core import Document, VectorStoreIndex, Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.faiss import FaissVectorStore
    import faiss
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    logger.warning("LlamaIndex 套件未安裝，向量化功能將不可用")
    # 定義假的 Document 類型以避免類型錯誤
    Document = Any

from .text_processor import TextProcessor
from ..utils import FileHandler


class VectorProcessor:
    """向量處理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化向量處理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.text_processor = TextProcessor(config_manager)
        
        if not LLAMA_INDEX_AVAILABLE:
            logger.error("LlamaIndex 未安裝，無法使用向量化功能")
            return
        
        # 從配置取得向量化參數
        if config_manager:
            vector_config = config_manager.get("vectorization", {})
            self.embedding_model = vector_config.get(
                "embedding_model", 
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            self.vector_dimension = vector_config.get("vector_store", {}).get("dimension", 384)
            self.vector_db_dir = config_manager.get_data_directories()["vector_db"]
        else:
            self.embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            self.vector_dimension = 384
            self.vector_db_dir = "data/vector_db"
        
        # 初始化嵌入模型
        self.embedding = None
        self.index = None
        self._init_embedding_model()
    
    def _init_embedding_model(self) -> None:
        """初始化嵌入模型"""
        if not LLAMA_INDEX_AVAILABLE:
            return
        
        try:
            logger.info(f"初始化嵌入模型: {self.embedding_model}")
            self.embedding = HuggingFaceEmbedding(model_name=self.embedding_model)
            
            # 設定全域嵌入模型
            Settings.embed_model = self.embedding
            
            logger.info("嵌入模型初始化完成")
            
        except Exception as e:
            logger.error(f"嵌入模型初始化失敗: {e}")
    
    def create_vector_index(self, documents_data: Dict[str, Any]) -> bool:
        """
        建立向量索引
        
        Args:
            documents_data: 文件資料
            
        Returns:
            是否成功建立索引
        """
        if not LLAMA_INDEX_AVAILABLE or not self.embedding:
            logger.error("向量化功能不可用")
            return False
        
        try:
            logger.info("開始建立向量索引")
            
            # 準備文件
            documents = self._prepare_documents(documents_data)
            if not documents:
                logger.error("沒有可用的文件")
                return False
            
            logger.info(f"準備了 {len(documents)} 個文件")
            
            # 建立 FAISS 向量儲存
            faiss_index = faiss.IndexFlatIP(self.vector_dimension)
            vector_store = FaissVectorStore(faiss_index=faiss_index)
            
            # 建立索引
            self.index = VectorStoreIndex.from_documents(
                documents, 
                vector_store=vector_store
            )
            
            # 儲存索引
            self._save_index()
            
            logger.info("向量索引建立完成")
            return True
            
        except Exception as e:
            logger.error(f"建立向量索引失敗: {e}")
            return False
    
    def load_vector_index(self) -> bool:
        """
        載入已存在的向量索引

        Returns:
            是否成功載入
        """
        if not LLAMA_INDEX_AVAILABLE or not self.embedding:
            logger.error("向量化功能不可用")
            return False

        try:
            index_path = Path(self.vector_db_dir) / "index"

            if not index_path.exists():
                logger.warning("向量索引不存在")
                return False

            # 嘗試使用 LlamaIndex 的 load_index_from_storage
            from llama_index.core import load_index_from_storage, StorageContext

            storage_context = StorageContext.from_defaults(persist_dir=str(index_path))
            self.index = load_index_from_storage(storage_context)

            logger.info("向量索引載入完成")
            return True

        except Exception as e:
            logger.error(f"載入向量索引失敗: {e}")
            return False
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        執行向量搜尋
        
        Args:
            query: 搜尋查詢
            top_k: 返回結果數量
            similarity_threshold: 相似度閾值
            
        Returns:
            搜尋結果列表
        """
        if not LLAMA_INDEX_AVAILABLE or not self.index:
            logger.error("向量索引不可用")
            return []
        
        try:
            logger.info(f"執行搜尋: {query}")

            # 使用檢索器而不是查詢引擎（避免需要 LLM）
            retriever = self.index.as_retriever(similarity_top_k=top_k)

            # 執行檢索
            nodes = retriever.retrieve(query)

            # 處理結果
            results = []
            for node in nodes:
                score = node.score if hasattr(node, 'score') else 1.0

                if score is not None and score >= similarity_threshold:
                    result = {
                        "content": node.text,
                        "score": score,
                        "metadata": node.metadata if hasattr(node, 'metadata') else {}
                    }
                    results.append(result)

            logger.info(f"搜尋完成，找到 {len(results)} 個結果")
            return results
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []
    
    def _prepare_documents(self, documents_data: Dict[str, Any]) -> List[Any]:
        """
        準備文件用於向量化
        
        Args:
            documents_data: 文件資料
            
        Returns:
            Document 物件列表
        """
        documents = []
        
        try:
            # 處理所有文件（包括新聞和人事資料）
            all_docs = documents_data.get("documents", [])

            for doc_info in all_docs:
                source = doc_info.get("source", "")

                if source == "news":
                    # 處理新聞文章（有完整內容）
                    content = doc_info.get("content", "")
                    title = doc_info.get("title", "")

                    if content:
                        # 處理文本
                        processed_content = self.text_processor.clean_text(content)
                        chunks = self.text_processor.split_text_into_chunks(processed_content)

                        # 為每個塊建立文件
                        for i, chunk in enumerate(chunks):
                            metadata = {
                                "id": f"{doc_info.get('id', '')}_chunk_{i}",
                                "title": title,
                                "url": doc_info.get("url", ""),
                                "source": "news",
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            }

                            if LLAMA_INDEX_AVAILABLE:
                                doc = Document(text=chunk, metadata=metadata)
                            else:
                                doc = {"text": chunk, "metadata": metadata}
                            documents.append(doc)

                    # 也為標題建立一個文件
                    if title:
                        metadata = {
                            "id": doc_info.get("id", ""),
                            "title": title,
                            "url": doc_info.get("url", ""),
                            "source": "news",
                            "type": "title"
                        }

                        if LLAMA_INDEX_AVAILABLE:
                            doc = Document(text=title, metadata=metadata)
                        else:
                            doc = {"text": title, "metadata": metadata}
                        documents.append(doc)

                elif source == "personnel":
                    # 處理人事文件（僅標題，因為 PDF 內容無法直接提取）
                    title = doc_info.get("title", "")
                    if title:
                        metadata = {
                            "id": doc_info.get("id", ""),
                            "title": title,
                            "url": doc_info.get("url", ""),
                            "source": "personnel",
                            "category": doc_info.get("category", ""),
                            "type": doc_info.get("type", "")
                        }

                        if LLAMA_INDEX_AVAILABLE:
                            doc = Document(text=title, metadata=metadata)
                        else:
                            doc = {"text": title, "metadata": metadata}
                        documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"準備文件失敗: {e}")
            return []
    
    def _save_index(self) -> None:
        """儲存向量索引"""
        try:
            index_dir = Path(self.vector_db_dir) / "index"
            FileHandler.ensure_directory(index_dir)
            
            # 儲存 FAISS 索引
            if hasattr(self.index, 'vector_store') and hasattr(self.index.vector_store, 'faiss_index'):
                faiss.write_index(
                    self.index.vector_store.faiss_index,
                    str(index_dir / "vector_store.faiss")
                )
                logger.info(f"FAISS 索引已儲存")
            else:
                logger.warning("無法存取 FAISS 索引，嘗試使用 persist 方法")
                # 嘗試使用 LlamaIndex 的 persist 方法
                if hasattr(self.index, 'storage_context'):
                    self.index.storage_context.persist(persist_dir=str(index_dir))
                    logger.info(f"使用 persist 方法儲存索引")
            
            # 儲存元資料
            metadata = {
                "embedding_model": self.embedding_model,
                "vector_dimension": self.vector_dimension,
                "created_timestamp": self._get_timestamp()
            }
            
            FileHandler.save_json_file(index_dir / "metadata.json", metadata)
            
            logger.info(f"向量索引已儲存到: {index_dir}")
            
        except Exception as e:
            logger.error(f"儲存向量索引失敗: {e}")
    
    def _get_timestamp(self) -> str:
        """取得當前時間戳記"""
        from datetime import datetime
        return datetime.now().isoformat()
