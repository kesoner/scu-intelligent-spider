import { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { Send, ArrowLeft, Bot, User, ExternalLink } from 'lucide-react';
import { apiClient, QuestionRequest, QuestionResponse } from '../lib/api';

interface Message {
  id: string;
  type: 'user' | 'bot';
  content: string;
  sources?: QuestionResponse['sources'];
  timestamp: Date;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'bot',
      content: '您好！我是東吳大學智能助理。您可以問我關於東吳大學的任何問題，例如：\n\n• 東吳大學商學院有什麼認證？\n• 東吳大學有哪些國際合作項目？\n• 東吳大學學生的表現如何？',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [settings, setSettings] = useState({
    topK: 5,
    threshold: 0.3,
    useLLM: 'none' as 'none' | 'gemini' | 'local',
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const request: QuestionRequest = {
        question: inputValue,
        top_k: settings.topK,
        threshold: settings.threshold,
        use_llm: settings.useLLM,
      };

      const response = await apiClient.askQuestion(request);

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: response.success 
          ? response.answer || '抱歉，我無法回答這個問題。'
          : `錯誤：${response.error}`,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        content: '抱歉，系統發生錯誤，請稍後再試。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const suggestedQuestions = [
    '東吳大學商學院有什麼認證？',
    '東吳大學有哪些國際合作項目？',
    '東吳大學學生在程式設計方面有什麼成就？',
    '東吳大學的環保計畫是什麼？',
  ];

  return (
    <>
      <Head>
        <title>智能問答 - 東吳大學智能爬蟲系統</title>
        <meta name="description" content="與東吳大學智能助理對話，獲得準確的資訊回答" />
      </Head>

      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between py-4">
              <div className="flex items-center">
                <Link href="/" className="mr-4">
                  <ArrowLeft className="h-6 w-6 text-gray-600 hover:text-gray-900" />
                </Link>
                <h1 className="text-xl font-semibold text-gray-900">智能問答</h1>
              </div>
              
              {/* Settings */}
              <div className="flex items-center space-x-4">
                <div className="text-sm text-gray-600">
                  <label className="mr-2">AI 模型:</label>
                  <select
                    value={settings.useLLM}
                    onChange={(e) => setSettings(prev => ({ ...prev, useLLM: e.target.value as 'none' | 'gemini' | 'local' }))}
                    className="border border-gray-300 rounded px-2 py-1"
                  >
                    <option value="none">基於檢索</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="local">本地模型</option>
                  </select>
                </div>
                <div className="text-sm text-gray-600">
                  <label className="mr-2">結果數:</label>
                  <select
                    value={settings.topK}
                    onChange={(e) => setSettings(prev => ({ ...prev, topK: parseInt(e.target.value) }))}
                    className="border border-gray-300 rounded px-2 py-1"
                  >
                    <option value={3}>3</option>
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                  </select>
                </div>
                <div className="text-sm text-gray-600">
                  <label className="mr-2">閾值:</label>
                  <select
                    value={settings.threshold}
                    onChange={(e) => setSettings(prev => ({ ...prev, threshold: parseFloat(e.target.value) }))}
                    className="border border-gray-300 rounded px-2 py-1"
                  >
                    <option value={0.1}>0.1</option>
                    <option value={0.3}>0.3</option>
                    <option value={0.5}>0.5</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-hidden">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="bg-white rounded-lg shadow-sm border h-full flex flex-col">
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`flex max-w-3xl ${message.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      {/* Avatar */}
                      <div className={`flex-shrink-0 ${message.type === 'user' ? 'ml-3' : 'mr-3'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          message.type === 'user' 
                            ? 'bg-primary-600 text-white' 
                            : 'bg-gray-200 text-gray-600'
                        }`}>
                          {message.type === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                        </div>
                      </div>

                      {/* Message Content */}
                      <div className={`rounded-lg px-4 py-3 ${
                        message.type === 'user'
                          ? 'bg-primary-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}>
                        <div className="whitespace-pre-wrap">{message.content}</div>
                        
                        {/* Sources */}
                        {message.sources && message.sources.length > 0 && (
                          <div className="mt-4 pt-3 border-t border-gray-300">
                            <div className="text-sm font-medium mb-2">參考資料：</div>
                            <div className="space-y-2">
                              {message.sources.map((source, index) => (
                                <div key={index} className="text-sm">
                                  <div className="font-medium">{source.title}</div>
                                  <div className="text-gray-600 text-xs">
                                    來源: {source.source} | 相似度: {source.score.toFixed(3)}
                                  </div>
                                  {source.url && (
                                    <a
                                      href={source.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center text-xs text-blue-600 hover:text-blue-800"
                                    >
                                      查看原文 <ExternalLink className="h-3 w-3 ml-1" />
                                    </a>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        <div className="text-xs opacity-70 mt-2">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="flex mr-3">
                      <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center">
                        <Bot className="h-4 w-4" />
                      </div>
                    </div>
                    <div className="bg-gray-100 rounded-lg px-4 py-3">
                      <div className="flex items-center space-x-2">
                        <div className="loading-spinner"></div>
                        <span className="text-gray-600">思考中...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Questions */}
              {messages.length === 1 && (
                <div className="px-6 py-4 border-t bg-gray-50">
                  <div className="text-sm font-medium text-gray-700 mb-2">建議問題：</div>
                  <div className="flex flex-wrap gap-2">
                    {suggestedQuestions.map((question, index) => (
                      <button
                        key={index}
                        onClick={() => setInputValue(question)}
                        className="text-sm bg-white border border-gray-300 rounded-full px-3 py-1 hover:bg-gray-50 transition-colors"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input */}
              <div className="p-6 border-t">
                <form onSubmit={handleSubmit} className="flex space-x-4">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="請輸入您的問題..."
                    className="flex-1 input-field"
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={!inputValue.trim() || isLoading}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
