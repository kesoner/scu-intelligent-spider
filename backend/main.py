#!/usr/bin/env python3
"""
東吳大學智能爬蟲系統 - FastAPI 後端

提供 RESTful API 服務
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils import ConfigManager
from src.processors.simple_rag_processor import SimpleRAGProcessor
from src.crawlers import PersonnelCrawler, NewsCrawler
from src.processors import DataFormatter, VectorProcessor
from loguru import logger

# 初始化 FastAPI 應用
app = FastAPI(
    title="東吳大學智能爬蟲系統 API",
    description="提供爬蟲、資料處理和智能問答功能的 RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js 開發伺服器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域變數
config = None
rag_processor = None

# Pydantic 模型
class QuestionRequest(BaseModel):
    question: str
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.3
    use_llm: Optional[str] = "none"  # "none", "gemini", "local"

class QuestionResponse(BaseModel):
    success: bool
    question: str
    answer: Optional[str] = None
    sources: Optional[List[Dict]] = None
    retrieved_count: Optional[int] = None
    error: Optional[str] = None

class CrawlRequest(BaseModel):
    target: str  # "personnel", "news", "all"
    pages: Optional[int] = None

class CrawlResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.3

class SearchResponse(BaseModel):
    success: bool
    query: str
    results: Optional[List[Dict]] = None
    count: Optional[int] = None
    error: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    components: Dict[str, Any]
    data_info: Dict[str, Any]

@app.on_event("startup")
async def startup_event():
    """應用啟動時初始化"""
    global config, rag_processor
    
    try:
        # 初始化配置
        config = ConfigManager()
        logger.info("配置管理器初始化完成")
        
        # 初始化 RAG 處理器
        rag_processor = SimpleRAGProcessor(config)
        logger.info("RAG 處理器初始化完成")
        
        logger.info("FastAPI 應用啟動完成")
        
    except Exception as e:
        logger.error(f"應用啟動失敗: {e}")
        raise

@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": "東吳大學智能爬蟲系統 API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "timestamp": "2025-06-22"}

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """獲取系統狀態"""
    try:
        # 檢查各組件狀態
        components = {
            "config": "ok" if config else "error",
            "rag_processor": "ok" if rag_processor else "error",
            "vector_index": "unknown"
        }
        
        # 檢查向量索引
        try:
            vector_processor = VectorProcessor(config)
            if vector_processor.load_vector_index():
                components["vector_index"] = "ok"
            else:
                components["vector_index"] = "not_found"
        except Exception:
            components["vector_index"] = "error"
        
        # 檢查資料檔案
        data_info = {
            "raw_data": {},
            "processed_data": {},
            "vector_db": {}
        }
        
        # 檢查原始資料
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            data_info["raw_data"] = {
                "personnel_data": (raw_dir / "personnel_data.json").exists(),
                "news_data": (raw_dir / "news_data.json").exists(),
                "pdf_links": (raw_dir / "pdf_links.txt").exists(),
                "news_texts": (raw_dir / "news_texts.txt").exists()
            }
        
        # 檢查處理資料
        processed_dir = Path("data/processed")
        if processed_dir.exists():
            processed_files = list(processed_dir.glob("scu_data_*.json"))
            data_info["processed_data"] = {
                "count": len(processed_files),
                "latest": processed_files[-1].name if processed_files else None
            }
        
        # 檢查向量資料庫
        vector_dir = Path("data/vector_db")
        if vector_dir.exists():
            data_info["vector_db"] = {
                "index_exists": (vector_dir / "index").exists(),
                "metadata_exists": (vector_dir / "metadata.json").exists()
            }
        
        return SystemStatus(
            status="running",
            components=components,
            data_info=data_info
        )
        
    except Exception as e:
        logger.error(f"獲取系統狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """智能問答"""
    try:
        if not config:
            raise HTTPException(status_code=500, detail="配置管理器未初始化")

        # 根據請求創建適當的 RAG 處理器
        if request.use_llm and request.use_llm != "none":
            current_rag_processor = SimpleRAGProcessor(config, use_llm=request.use_llm)
        else:
            current_rag_processor = rag_processor or SimpleRAGProcessor(config)

        # 執行問答
        result = current_rag_processor.answer_question(
            request.question,
            top_k=request.top_k or 5,
            similarity_threshold=request.threshold or 0.3
        )

        if result.get("success"):
            return QuestionResponse(
                success=True,
                question=request.question,
                answer=result["answer"],
                sources=result.get("sources", []),
                retrieved_count=result.get("retrieved_count", 0)
            )
        else:
            return QuestionResponse(
                success=False,
                question=request.question,
                error=result.get("error", "未知錯誤")
            )

    except Exception as e:
        logger.error(f"問答處理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """向量搜尋"""
    try:
        vector_processor = VectorProcessor(config)
        
        if not vector_processor.load_vector_index():
            raise HTTPException(status_code=404, detail="向量索引不存在，請先建立索引")
        
        # 執行搜尋
        results = vector_processor.search(
            request.query,
            top_k=request.top_k or 5,
            similarity_threshold=request.threshold or 0.3
        )
        
        return SearchResponse(
            success=True,
            query=request.query,
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        logger.error(f"搜尋失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_crawler_task(target: str, pages: Optional[int] = None):
    """執行爬蟲任務（背景任務）"""
    try:
        if target == "personnel":
            with PersonnelCrawler(config) as crawler:
                result = crawler.crawl()
            return {"type": "personnel", "result": result}
            
        elif target == "news":
            if pages:
                config._config['websites']['news']['max_pages'] = pages
            with NewsCrawler(config) as crawler:
                result = crawler.crawl()
            return {"type": "news", "result": result}
            
        elif target == "all":
            results = {}
            
            # 爬取人事資料
            with PersonnelCrawler(config) as crawler:
                results["personnel"] = crawler.crawl()
            
            # 爬取新聞資料
            if pages:
                config._config['websites']['news']['max_pages'] = pages
            with NewsCrawler(config) as crawler:
                results["news"] = crawler.crawl()
            
            return {"type": "all", "result": results}
        else:
            raise ValueError(f"不支援的爬蟲目標: {target}")
            
    except Exception as e:
        logger.error(f"爬蟲任務失敗: {e}")
        return {"type": target, "error": str(e)}

@app.post("/api/crawl", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """啟動爬蟲任務"""
    try:
        # 驗證目標
        if request.target not in ["personnel", "news", "all"]:
            raise HTTPException(status_code=400, detail="無效的爬蟲目標")
        
        # 添加背景任務
        background_tasks.add_task(run_crawler_task, request.target, request.pages)
        
        return CrawlResponse(
            success=True,
            message=f"爬蟲任務已啟動: {request.target}",
            details={
                "target": request.target,
                "pages": request.pages,
                "status": "started"
            }
        )
        
    except Exception as e:
        logger.error(f"啟動爬蟲失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-data")
async def process_data(background_tasks: BackgroundTasks):
    """處理資料"""
    try:
        def process_task():
            try:
                formatter = DataFormatter(config)
                
                # 載入原始資料
                personnel_data = formatter.load_personnel_data()
                news_data = formatter.load_news_data()
                
                # 格式化資料
                formatted_personnel = formatter.format_personnel_data(personnel_data)
                formatted_news = formatter.format_news_data(news_data)
                
                # 合併資料
                merged_data = formatter.merge_datasets(formatted_personnel, formatted_news)
                
                # 匯出多種格式
                output_files = formatter.export_to_formats(
                    merged_data,
                    "data/processed",
                    ['json', 'csv']
                )
                
                logger.info(f"資料處理完成: {output_files}")
                return output_files
                
            except Exception as e:
                logger.error(f"資料處理任務失敗: {e}")
                return {"error": str(e)}
        
        # 添加背景任務
        background_tasks.add_task(process_task)
        
        return {
            "success": True,
            "message": "資料處理任務已啟動",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"啟動資料處理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build-index")
async def build_vector_index(background_tasks: BackgroundTasks):
    """建立向量索引"""
    try:
        def build_task():
            try:
                vector_processor = VectorProcessor(config)
                success = vector_processor.build_vector_index()
                
                if success:
                    logger.info("向量索引建立完成")
                    return {"success": True}
                else:
                    logger.error("向量索引建立失敗")
                    return {"success": False, "error": "建立失敗"}
                    
            except Exception as e:
                logger.error(f"向量索引建立任務失敗: {e}")
                return {"success": False, "error": str(e)}
        
        # 添加背景任務
        background_tasks.add_task(build_task)
        
        return {
            "success": True,
            "message": "向量索引建立任務已啟動",
            "status": "started"
        }
        
    except Exception as e:
        logger.error(f"啟動向量索引建立失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
