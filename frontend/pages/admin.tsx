import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Download, 
  Database, 
  RefreshCw, 
  Settings, 
  Play,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { apiClient, SystemStatus, CrawlRequest } from '../lib/api';

type TaskStatus = 'idle' | 'running' | 'success' | 'error';

interface Task {
  id: string;
  name: string;
  description: string;
  status: TaskStatus;
  message?: string;
}

export default function Admin() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<Task[]>([
    {
      id: 'crawl-personnel',
      name: '爬取人事資料',
      description: '從東吳大學人事網站爬取最新的人事資料',
      status: 'idle'
    },
    {
      id: 'crawl-news',
      name: '爬取新聞資料',
      description: '從東吳大學新聞網站爬取最新的新聞內容',
      status: 'idle'
    },
    {
      id: 'process-data',
      name: '處理資料',
      description: '清理和格式化爬取的原始資料',
      status: 'idle'
    },
    {
      id: 'build-index',
      name: '建立向量索引',
      description: '為搜尋和問答功能建立向量索引',
      status: 'idle'
    }
  ]);

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

  const updateTaskStatus = (taskId: string, status: TaskStatus, message?: string) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId 
        ? { ...task, status, message }
        : task
    ));
  };

  const runTask = async (taskId: string) => {
    updateTaskStatus(taskId, 'running');

    try {
      switch (taskId) {
        case 'crawl-personnel':
          await apiClient.startCrawl({ target: 'personnel' });
          updateTaskStatus(taskId, 'success', '人事資料爬取任務已啟動');
          break;
          
        case 'crawl-news':
          await apiClient.startCrawl({ target: 'news', pages: 10 });
          updateTaskStatus(taskId, 'success', '新聞資料爬取任務已啟動');
          break;
          
        case 'process-data':
          await apiClient.processData();
          updateTaskStatus(taskId, 'success', '資料處理任務已啟動');
          break;
          
        case 'build-index':
          await apiClient.buildIndex();
          updateTaskStatus(taskId, 'success', '向量索引建立任務已啟動');
          break;
          
        default:
          throw new Error('未知的任務類型');
      }
      
      // 延遲更新系統狀態
      setTimeout(fetchSystemStatus, 2000);
      
    } catch (error) {
      console.error(`Task ${taskId} failed:`, error);
      updateTaskStatus(taskId, 'error', '任務執行失敗');
    }
  };

  const runAllTasks = async () => {
    const taskOrder = ['crawl-personnel', 'crawl-news', 'process-data', 'build-index'];
    
    for (const taskId of taskOrder) {
      await runTask(taskId);
      // 等待一段時間再執行下一個任務
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  };

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case 'running':
        return <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
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
        <title>系統管理 - 東吳大學智能爬蟲系統</title>
        <meta name="description" content="管理爬蟲系統，執行資料爬取和處理任務" />
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
                <h1 className="text-xl font-semibold text-gray-900">系統管理</h1>
              </div>
              
              <button
                onClick={fetchSystemStatus}
                className="btn-secondary"
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                重新整理
              </button>
            </div>
          </div>
        </header>

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
          {/* System Status */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold flex items-center">
                <Settings className="h-5 w-5 mr-2" />
                系統狀態
              </h2>
            </div>

            {loading ? (
              <div className="flex justify-center py-8">
                <div className="loading-spinner"></div>
              </div>
            ) : systemStatus ? (
              <div className="space-y-6">
                {/* Components Status */}
                <div>
                  <h3 className="font-medium mb-3">組件狀態</h3>
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

                {/* Data Status */}
                <div>
                  <h3 className="font-medium mb-3">資料狀態</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-2">原始資料</div>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div>人事資料: {systemStatus.data_info.raw_data?.personnel_data ? '✓' : '✗'}</div>
                        <div>新聞資料: {systemStatus.data_info.raw_data?.news_data ? '✓' : '✗'}</div>
                        <div>PDF 連結: {systemStatus.data_info.raw_data?.pdf_links ? '✓' : '✗'}</div>
                        <div>新聞文字: {systemStatus.data_info.raw_data?.news_texts ? '✓' : '✗'}</div>
                      </div>
                    </div>
                    
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-2">處理資料</div>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div>檔案數量: {systemStatus.data_info.processed_data?.count || 0}</div>
                        <div>最新檔案: {systemStatus.data_info.processed_data?.latest || '無'}</div>
                      </div>
                    </div>
                    
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <div className="text-sm font-medium mb-2">向量資料庫</div>
                      <div className="space-y-1 text-xs text-gray-600">
                        <div>索引: {systemStatus.data_info.vector_db?.index_exists ? '✓' : '✗'}</div>
                        <div>元資料: {systemStatus.data_info.vector_db?.metadata_exists ? '✓' : '✗'}</div>
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

          {/* Task Management */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold flex items-center">
                <Database className="h-5 w-5 mr-2" />
                任務管理
              </h2>
              <button
                onClick={runAllTasks}
                className="btn-primary"
                disabled={tasks.some(task => task.status === 'running')}
              >
                <Play className="h-4 w-4 mr-2" />
                執行全部任務
              </button>
            </div>

            <div className="space-y-4">
              {tasks.map((task) => (
                <div key={task.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(task.status)}
                    <div>
                      <div className="font-medium text-gray-900">{task.name}</div>
                      <div className="text-sm text-gray-600">{task.description}</div>
                      {task.message && (
                        <div className="text-xs text-gray-500 mt-1">{task.message}</div>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => runTask(task.id)}
                    disabled={task.status === 'running'}
                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {task.status === 'running' ? '執行中...' : '執行'}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="card">
            <h2 className="text-lg font-semibold mb-6 flex items-center">
              <Download className="h-5 w-5 mr-2" />
              快速操作
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => runTask('crawl-personnel')}
                className="p-4 text-left border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                disabled={tasks.find(t => t.id === 'crawl-personnel')?.status === 'running'}
              >
                <div className="font-medium text-gray-900">快速爬取人事資料</div>
                <div className="text-sm text-gray-600 mt-1">
                  立即爬取最新的人事異動和公告資料
                </div>
              </button>
              
              <button
                onClick={() => runTask('crawl-news')}
                className="p-4 text-left border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                disabled={tasks.find(t => t.id === 'crawl-news')?.status === 'running'}
              >
                <div className="font-medium text-gray-900">快速爬取新聞資料</div>
                <div className="text-sm text-gray-600 mt-1">
                  立即爬取最新的校園新聞和活動資訊
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
