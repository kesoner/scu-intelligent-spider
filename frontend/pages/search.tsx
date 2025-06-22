import { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { Search, ArrowLeft, ExternalLink, Filter } from 'lucide-react';
import { apiClient, SearchRequest, SearchResponse } from '../lib/api';

interface SearchResult {
  content: string;
  score: number;
  metadata: {
    title: string;
    url: string;
    source: string;
  };
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [settings, setSettings] = useState({
    topK: 10,
    threshold: 0.3,
  });
  const [showSettings, setShowSettings] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setHasSearched(true);

    try {
      const request: SearchRequest = {
        query: query.trim(),
        top_k: settings.topK,
        threshold: settings.threshold,
      };

      const response = await apiClient.searchDocuments(request);

      if (response.success && response.results) {
        setResults(response.results);
      } else {
        setResults([]);
      }
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const highlightText = (text: string, query: string) => {
    if (!query) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'news':
        return 'bg-blue-100 text-blue-800';
      case 'personnel':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'news':
        return '新聞';
      case 'personnel':
        return '人事';
      default:
        return source;
    }
  };

  return (
    <>
      <Head>
        <title>資料搜尋 - 東吳大學智能爬蟲系統</title>
        <meta name="description" content="搜尋東吳大學相關資料，使用 AI 向量搜尋技術" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-4">
              <div className="flex items-center">
                <Link href="/" className="mr-4">
                  <ArrowLeft className="h-6 w-6 text-gray-600 hover:text-gray-900" />
                </Link>
                <h1 className="text-xl font-semibold text-gray-900">資料搜尋</h1>
              </div>
              
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="flex items-center text-gray-600 hover:text-gray-900"
              >
                <Filter className="h-5 w-5 mr-1" />
                設定
              </button>
            </div>
          </div>
        </header>

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Search Form */}
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-8">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="flex space-x-4">
                <div className="flex-1">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="輸入搜尋關鍵字..."
                    className="input-field"
                    disabled={isLoading}
                  />
                </div>
                <button
                  type="submit"
                  disabled={!query.trim() || isLoading}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  <Search className="h-4 w-4 mr-2" />
                  {isLoading ? '搜尋中...' : '搜尋'}
                </button>
              </div>

              {/* Settings Panel */}
              {showSettings && (
                <div className="border-t pt-4 mt-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        結果數量
                      </label>
                      <select
                        value={settings.topK}
                        onChange={(e) => setSettings(prev => ({ ...prev, topK: parseInt(e.target.value) }))}
                        className="input-field"
                      >
                        <option value={5}>5 個結果</option>
                        <option value={10}>10 個結果</option>
                        <option value={20}>20 個結果</option>
                        <option value={50}>50 個結果</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        相似度閾值
                      </label>
                      <select
                        value={settings.threshold}
                        onChange={(e) => setSettings(prev => ({ ...prev, threshold: parseFloat(e.target.value) }))}
                        className="input-field"
                      >
                        <option value={0.1}>0.1 (寬鬆)</option>
                        <option value={0.3}>0.3 (平衡)</option>
                        <option value={0.5}>0.5 (嚴格)</option>
                        <option value={0.7}>0.7 (非常嚴格)</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}
            </form>
          </div>

          {/* Search Results */}
          {isLoading && (
            <div className="flex justify-center py-12">
              <div className="flex items-center space-x-3">
                <div className="loading-spinner"></div>
                <span className="text-gray-600">搜尋中...</span>
              </div>
            </div>
          )}

          {hasSearched && !isLoading && (
            <div className="space-y-6">
              {/* Results Header */}
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">
                  搜尋結果
                  {results.length > 0 && (
                    <span className="text-gray-500 font-normal ml-2">
                      ({results.length} 個結果)
                    </span>
                  )}
                </h2>
                {query && (
                  <div className="text-sm text-gray-600">
                    搜尋關鍵字: <span className="font-medium">"{query}"</span>
                  </div>
                )}
              </div>

              {/* Results List */}
              {results.length > 0 ? (
                <div className="space-y-4">
                  {results.map((result, index) => (
                    <div key={index} className="bg-white rounded-lg shadow-sm border p-6 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="text-lg font-medium text-gray-900 mb-1">
                            {result.metadata.title}
                          </h3>
                          <div className="flex items-center space-x-3 text-sm text-gray-600">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSourceBadgeColor(result.metadata.source)}`}>
                              {getSourceLabel(result.metadata.source)}
                            </span>
                            <span>相似度: {result.score.toFixed(3)}</span>
                          </div>
                        </div>
                        {result.metadata.url && (
                          <a
                            href={result.metadata.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center text-primary-600 hover:text-primary-800 text-sm"
                          >
                            查看原文 <ExternalLink className="h-4 w-4 ml-1" />
                          </a>
                        )}
                      </div>
                      
                      <div className="text-gray-700 leading-relaxed">
                        {highlightText(result.content, query)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">沒有找到相關結果</h3>
                  <p className="text-gray-600 mb-4">
                    請嘗試使用不同的關鍵字或降低相似度閾值
                  </p>
                  <div className="space-y-2 text-sm text-gray-500">
                    <p>建議：</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>使用更簡單的關鍵字</li>
                      <li>檢查拼寫是否正確</li>
                      <li>嘗試相關的同義詞</li>
                      <li>降低相似度閾值到 0.1</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Search Tips */}
          {!hasSearched && (
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">搜尋技巧</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">建議搜尋關鍵字</h4>
                  <ul className="space-y-1 text-sm text-gray-600">
                    <li>• 東吳大學商學院認證</li>
                    <li>• 國際合作項目</li>
                    <li>• 學生競賽成果</li>
                    <li>• 環保永續計畫</li>
                    <li>• 校友創業表現</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">搜尋設定說明</h4>
                  <ul className="space-y-1 text-sm text-gray-600">
                    <li>• <strong>結果數量</strong>: 控制返回的搜尋結果數量</li>
                    <li>• <strong>相似度閾值</strong>: 控制搜尋結果的相關性</li>
                    <li>• 閾值越高，結果越精確但數量可能較少</li>
                    <li>• 閾值越低，結果越多但相關性可能較低</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
