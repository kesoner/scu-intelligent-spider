@echo off
echo 🚀 上傳東吳大學智能爬蟲系統到 GitHub
echo ================================================

echo 📁 初始化 Git 倉庫...
git init

echo 📝 設定 Git 配置...
git config user.name "SCU Spider Developer"
git config user.email "developer@example.com"

echo 📋 添加所有文件...
git add .

echo 💾 建立初始提交...
git commit -m "Initial commit: 東吳大學智能爬蟲系統 - AI 驅動的知識管理平台

✨ 功能特色:
🤖 Google Gemini 智能問答
🔍 向量搜尋技術
🌐 現代化 Web 介面 (FastAPI + Next.js)
🕷️ 智能爬蟲系統
📊 完整資料處理流程

🛠️ 技術棧:
- 後端: FastAPI + Python 3.11
- 前端: Next.js 14 + React 18 + TypeScript
- AI: Google Gemini + RAG + 向量搜尋
- 資料庫: FAISS 向量資料庫
- 樣式: Tailwind CSS"

echo 🔗 請手動執行以下命令來連接到你的 GitHub 倉庫:
echo git remote add origin https://github.com/your-username/your-repo-name.git
echo git branch -M main
echo git push -u origin main

echo.
echo ✅ Git 倉庫初始化完成！
echo 💡 請將上面的 GitHub 倉庫 URL 替換為你的實際倉庫地址
echo.
pause
