import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { Search, MessageCircle, Database, Settings, Activity } from 'lucide-react';
import { apiClient, SystemStatus } from '../lib/api';

export default function Home() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  const fetchSystemStatus = async () => {
    try {
      setLoading(true);
      const status = await apiClient.getSystemStatus();
      setSystemStatus(status);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok':
        return 'text-green-600 bg-green-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      case 'not_found':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <>
      <Head>
        <title>東吳大學智能爬蟲系統</title>
        <meta name="description" content="東吳大學智能爬蟲系統 - 提供智能問答和資料檢索功能" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        {/* Header */}
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <h1 className="text-2xl font-bold text-gradient">
                    🕷️ 東吳大學智能爬蟲系統
                  </h1>
                </div>
              </div>
              <nav className="hidden md:flex space-x-8">
                <Link href="/search" className="text-gray-600 hover:text-gray-900">
                  搜尋
                </Link>
                <Link href="/chat" className="text-gray-600 hover:text-gray-900">
                  問答
                </Link>
                <Link href="/admin" className="text-gray-600 hover:text-gray-900">
                  管理
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Hero Section */}
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              智能資料檢索與問答系統
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              基於 AI 技術的東吳大學資料爬取、處理和智能問答平台
            </p>
            <div className="flex justify-center space-x-4">
              <Link href="/chat" className="btn-primary">
                開始問答
              </Link>
              <Link href="/search" className="btn-secondary">
                搜尋資料
              </Link>
            </div>
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
            <div className="card text-center">
              <MessageCircle className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">智能問答</h3>
              <p className="text-gray-600">
                基於 RAG 技術的智能問答系統，提供準確的資訊回答
              </p>
            </div>
            
            <div className="card text-center">
              <Search className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">語意搜尋</h3>
              <p className="text-gray-600">
                使用向量搜尋技術，理解查詢意圖，提供相關資料
              </p>
            </div>
            
            <div className="card text-center">
              <Database className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">資料爬取</h3>
              <p className="text-gray-600">
                自動爬取東吳大學官網的人事和新聞資料
              </p>
            </div>
            
            <div className="card text-center">
              <Settings className="h-12 w-12 text-primary-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">系統管理</h3>
              <p className="text-gray-600">
                完整的系統管理功能，包括資料處理和索引建立
              </p>
            </div>
          </div>

          {/* System Status */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold flex items-center">
                <Activity className="h-5 w-5 mr-2" />
                系統狀態
              </h3>
              <button
                onClick={fetchSystemStatus}
                className="btn-secondary text-sm"
                disabled={loading}
              >
                {loading ? '更新中...' : '重新整理'}
              </button>
            </div>

            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : systemStatus ? (
              <div className="space-y-4">
                {/* Components Status */}
                <div>
                  <h4 className="font-medium mb-2">組件狀態</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(systemStatus.components).map(([key, status]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm font-medium capitalize">
                          {key.replace('_', ' ')}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
                          {status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Data Info */}
                <div>
                  <h4 className="font-medium mb-2">資料狀態</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-1">原始資料</div>
                      <div className="text-xs text-gray-600">
                        人事: {systemStatus.data_info.raw_data?.personnel_data ? '✓' : '✗'} |
                        新聞: {systemStatus.data_info.raw_data?.news_data ? '✓' : '✗'}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-1">處理資料</div>
                      <div className="text-xs text-gray-600">
                        檔案數: {systemStatus.data_info.processed_data?.count || 0}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-1">向量資料庫</div>
                      <div className="text-xs text-gray-600">
                        索引: {systemStatus.data_info.vector_db?.index_exists ? '✓' : '✗'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                無法載入系統狀態
              </div>
            )}
          </div>
        </main>

        {/* Footer */}
        <footer className="bg-white border-t">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="text-center text-gray-600">
              <p>&copy; 2025 東吳大學智能爬蟲系統. All rights reserved.</p>
              <p className="text-sm mt-2">
                Powered by FastAPI + Next.js + AI
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
