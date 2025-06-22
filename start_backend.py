#!/usr/bin/env python3
"""
啟動 FastAPI 後端服務
"""

import uvicorn
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("🚀 啟動東吳大學智能爬蟲系統 FastAPI 後端...")
    print("📡 API 文件: http://localhost:8000/docs")
    print("🔄 自動重載: 已啟用")
    print("=" * 50)
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
