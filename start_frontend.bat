@echo off
echo 🚀 啟動東吳大學智能爬蟲系統前端...
echo 🌐 前端地址: http://localhost:3000
echo 🔄 自動重載: 已啟用
echo ================================================

cd frontend

REM 檢查是否已安裝依賴
if not exist node_modules (
    echo 📦 安裝前端依賴...
    npm install
)

echo 🎯 啟動 Next.js 開發伺服器...
npm run dev
