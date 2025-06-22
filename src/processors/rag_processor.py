#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) 處理器

結合向量檢索和語言模型來回答問題
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

# 嘗試導入 LLM 相關套件
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI 套件未安裝，將使用本地模型")

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers 套件未安裝，RAG 功能將受限")

from .vector_processor import VectorProcessor


class RAGProcessor:
    """RAG 處理器類別"""
    
    def __init__(self, config, model_type: str = "local"):
        """
        初始化 RAG 處理器
        
        Args:
            config: 配置管理器
            model_type: 模型類型 ("openai", "local", "ollama")
        """
        self.config = config
        self.model_type = model_type
        self.vector_processor = VectorProcessor(config)
        
        # 初始化語言模型
        self.llm = None
        self.tokenizer = None
        self._initialize_llm()
        
        logger.info(f"RAG 處理器初始化完成，使用模型: {model_type}")
    
    def _initialize_llm(self):
        """初始化語言模型"""
        try:
            if self.model_type == "openai" and OPENAI_AVAILABLE:
                self._initialize_openai()
            elif self.model_type == "local" and TRANSFORMERS_AVAILABLE:
                self._initialize_local_model()
            elif self.model_type == "ollama":
                self._initialize_ollama()
            else:
                logger.warning("無可用的語言模型，將使用模板回應")
                
        except Exception as e:
            logger.error(f"語言模型初始化失敗: {e}")
            self.llm = None
    
    def _initialize_openai(self):
        """初始化 OpenAI 模型"""
        api_key = self.config.get("llm.openai.api_key")
        if not api_key:
            logger.warning("未設定 OpenAI API Key")
            return
            
        self.llm = OpenAI(api_key=api_key)
        logger.info("OpenAI 模型初始化完成")
    
    def _initialize_local_model(self):
        """初始化本地模型"""
        model_name = self.config.get("llm.local.model_name", "microsoft/DialoGPT-medium")
        
        try:
            # 使用較小的中文模型
            model_name = "ckiplab/gpt2-base-chinese"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # 設定 pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # 檢查是否有 GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.llm = pipeline(
                "text-generation",
                model=model_name,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                max_length=512,
                do_sample=True,
                temperature=0.7,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            logger.info(f"本地模型初始化完成: {model_name} (設備: {device})")
            
        except Exception as e:
            logger.error(f"本地模型載入失敗: {e}")
            # 降級到簡單的文本生成
            self.llm = None
    
    def _initialize_ollama(self):
        """初始化 Ollama 模型"""
        try:
            import requests
            
            # 測試 Ollama 連接
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                self.llm = "ollama"
                logger.info("Ollama 模型初始化完成")
            else:
                logger.warning("Ollama 服務未運行")
                
        except Exception as e:
            logger.error(f"Ollama 初始化失敗: {e}")
    
    def answer_question(self, question: str, top_k: int = 5, similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        回答問題
        
        Args:
            question: 使用者問題
            top_k: 檢索結果數量
            similarity_threshold: 相似度閾值
            
        Returns:
            包含答案和相關資訊的字典
        """
        logger.info(f"處理問題: {question}")
        
        try:
            # 1. 載入向量索引
            if not self.vector_processor.load_vector_index():
                return {
                    "success": False,
                    "error": "向量索引不存在，請先執行 build-index",
                    "question": question
                }
            
            # 2. 檢索相關文件
            retrieved_docs = self.vector_processor.search(
                question, 
                top_k=top_k, 
                similarity_threshold=similarity_threshold
            )
            
            if not retrieved_docs:
                return {
                    "success": False,
                    "error": "未找到相關資料",
                    "question": question,
                    "suggestions": self._get_search_suggestions()
                }
            
            # 3. 生成答案
            answer = self._generate_answer(question, retrieved_docs)
            
            # 4. 整理回應
            response = {
                "success": True,
                "question": question,
                "answer": answer,
                "sources": self._format_sources(retrieved_docs),
                "retrieved_count": len(retrieved_docs),
                "model_type": self.model_type
            }
            
            logger.info(f"問題回答完成，檢索到 {len(retrieved_docs)} 個相關文件")
            return response
            
        except Exception as e:
            logger.error(f"回答問題時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def _generate_answer(self, question: str, retrieved_docs: List[Dict]) -> str:
        """生成答案 - 優先使用基於檢索資料的直接回答"""
        # 準備上下文
        context = self._prepare_context(retrieved_docs)

        # 優先使用基於檢索資料的回答（更準確、更直接）
        template_answer = self._generate_template_answer(question, context)

        # 如果有高品質的語言模型且用戶明確要求，才使用 LLM
        if self.model_type == "openai" and self.llm and len(template_answer) < 100:
            try:
                llm_answer = self._generate_openai_answer(question, context)
                # 如果 LLM 回答更詳細且有用，則使用它
                if len(llm_answer) > len(template_answer) and "抱歉" not in llm_answer:
                    return llm_answer
            except:
                pass

        return template_answer
    
    def _prepare_context(self, retrieved_docs: List[Dict]) -> str:
        """準備上下文資訊"""
        context_parts = []
        
        for i, doc in enumerate(retrieved_docs, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            title = metadata.get("title", "未知標題")
            source = metadata.get("source", "未知來源")
            
            context_parts.append(f"文件 {i} (來源: {source}):\n標題: {title}\n內容: {content}\n")
        
        return "\n".join(context_parts)
    
    def _generate_openai_answer(self, question: str, context: str) -> str:
        """使用 OpenAI 生成答案"""
        try:
            if not OPENAI_AVAILABLE or not hasattr(self.llm, 'chat'):
                return self._generate_template_answer(question, context)

            prompt = f"""基於以下資料回答問題，請用繁體中文回答：

問題: {question}

相關資料:
{context}

請根據上述資料提供準確、詳細的回答。如果資料不足以回答問題，請說明並建議如何獲得更多資訊。
"""

            response = self.llm.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是東吳大學的智能助理，專門回答關於東吳大學的問題。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI 生成答案失敗: {e}")
            return self._generate_template_answer(question, context)
    
    def _generate_local_answer(self, question: str, context: str) -> str:
        """使用本地模型生成答案"""
        try:
            prompt = f"問題: {question}\n\n相關資料: {context[:500]}\n\n回答:"
            
            # 限制輸入長度
            max_input_length = 400
            if len(prompt) > max_input_length:
                prompt = prompt[:max_input_length] + "..."
            
            response = self.llm(
                prompt,
                max_new_tokens=150,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )
            
            generated_text = response[0]['generated_text']
            # 提取回答部分
            answer = generated_text.split("回答:")[-1].strip()
            
            return answer if answer else self._generate_template_answer(question, context)
            
        except Exception as e:
            logger.error(f"本地模型生成答案失敗: {e}")
            return self._generate_template_answer(question, context)
    
    def _generate_ollama_answer(self, question: str, context: str) -> str:
        """使用 Ollama 生成答案"""
        try:
            import requests
            
            prompt = f"""基於以下資料回答問題：

問題: {question}

相關資料:
{context[:800]}

請用繁體中文提供簡潔明確的回答。"""
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                return self._generate_template_answer(question, context)
                
        except Exception as e:
            logger.error(f"Ollama 生成答案失敗: {e}")
            return self._generate_template_answer(question, context)
    
    def _generate_template_answer(self, question: str, context: str) -> str:
        """基於檢索資料生成直接回答"""
        # 解析檢索到的文件
        documents = self._parse_context(context)

        if not documents:
            return "抱歉，我沒有找到相關的資料來回答您的問題。"

        # 根據問題類型生成回答
        question_lower = question.lower()

        if any(keyword in question for keyword in ["什麼", "是什麼", "哪些", "有什麼"]):
            return self._answer_what_question(question, documents)
        elif any(keyword in question for keyword in ["如何", "怎麼", "怎樣"]):
            return self._answer_how_question(question, documents)
        elif any(keyword in question for keyword in ["何時", "什麼時候", "時間"]):
            return self._answer_when_question(question, documents)
        elif any(keyword in question for keyword in ["在哪", "哪裡", "地點"]):
            return self._answer_where_question(question, documents)
        else:
            return self._answer_general_question(question, documents)

    def _parse_context(self, context: str) -> List[Dict]:
        """解析上下文中的文件資訊"""
        documents = []

        # 分割文件
        doc_sections = context.split("文件 ")

        for section in doc_sections[1:]:  # 跳過第一個空的部分
            try:
                lines = section.strip().split('\n')
                if len(lines) >= 3:
                    # 提取標題
                    title_line = [line for line in lines if line.startswith("標題:")][0]
                    title = title_line.replace("標題:", "").strip()

                    # 提取內容
                    content_start = False
                    content_lines = []
                    for line in lines:
                        if line.startswith("內容:"):
                            content_start = True
                            content_lines.append(line.replace("內容:", "").strip())
                        elif content_start and line.strip():
                            content_lines.append(line.strip())

                    content = " ".join(content_lines)

                    documents.append({
                        "title": title,
                        "content": content
                    })
            except:
                continue

        return documents

    def _answer_what_question(self, question: str, documents: List[Dict]) -> str:
        """回答 '什麼' 類型的問題"""
        answer_parts = []

        # 檢查是否詢問特定主題
        if "認證" in question:
            for doc in documents:
                if "認證" in doc["content"] or "AACSB" in doc["content"]:
                    answer_parts.append(f"• {doc['title']}: {doc['content']}")
        elif "合作" in question:
            for doc in documents:
                if "合作" in doc["content"] or "國際" in doc["content"]:
                    answer_parts.append(f"• {doc['title']}: {doc['content']}")
        elif "特色" in question:
            for doc in documents:
                if any(keyword in doc["content"] for keyword in ["特色", "優勢", "亮點", "成就"]):
                    answer_parts.append(f"• {doc['title']}: {doc['content']}")
        else:
            # 一般性回答
            for doc in documents[:3]:  # 限制前3個最相關的
                answer_parts.append(f"• {doc['title']}: {doc['content']}")

        if answer_parts:
            return "根據相關資料，我找到以下資訊：\n\n" + "\n\n".join(answer_parts)
        else:
            return "根據檢索到的資料，我找到了相關內容，但沒有直接回答您問題的具體資訊。建議您查看完整的相關文件。"

    def _answer_how_question(self, question: str, documents: List[Dict]) -> str:
        """回答 '如何' 類型的問題"""
        relevant_docs = []

        for doc in documents:
            if any(keyword in doc["content"] for keyword in ["申請", "步驟", "方法", "流程", "程序"]):
                relevant_docs.append(doc)

        if relevant_docs:
            answer = "根據相關資料，關於您詢問的方法：\n\n"
            for doc in relevant_docs[:2]:
                answer += f"• {doc['title']}: {doc['content']}\n\n"
            return answer
        else:
            return "抱歉，在檢索到的資料中沒有找到具體的操作方法。建議您聯繫相關部門獲得詳細指導。"

    def _answer_when_question(self, question: str, documents: List[Dict]) -> str:
        """回答 '何時' 類型的問題"""
        time_related_docs = []

        for doc in documents:
            if any(keyword in doc["content"] for keyword in ["時間", "日期", "期間", "截止", "開始"]):
                time_related_docs.append(doc)

        if time_related_docs:
            answer = "根據相關資料，關於時間資訊：\n\n"
            for doc in time_related_docs[:2]:
                answer += f"• {doc['title']}: {doc['content']}\n\n"
            return answer
        else:
            return "在檢索到的資料中沒有找到具體的時間資訊。建議查看最新的官方公告。"

    def _answer_where_question(self, question: str, documents: List[Dict]) -> str:
        """回答 '在哪' 類型的問題"""
        location_docs = []

        for doc in documents:
            if any(keyword in doc["content"] for keyword in ["地點", "位置", "地址", "校區", "辦公室"]):
                location_docs.append(doc)

        if location_docs:
            answer = "根據相關資料，關於地點資訊：\n\n"
            for doc in location_docs[:2]:
                answer += f"• {doc['title']}: {doc['content']}\n\n"
            return answer
        else:
            return "在檢索到的資料中沒有找到具體的地點資訊。建議聯繫相關部門確認。"

    def _answer_general_question(self, question: str, documents: List[Dict]) -> str:
        """回答一般性問題"""
        # 根據問題關鍵字找最相關的文件
        relevant_docs = []

        # 提取問題中的關鍵字
        keywords = []
        for word in question.split():
            if len(word) > 1 and word not in ["東吳", "大學", "的", "是", "有", "在", "和", "與"]:
                keywords.append(word)

        # 找包含關鍵字的文件
        for doc in documents:
            relevance_score = 0
            for keyword in keywords:
                if keyword in doc["content"] or keyword in doc["title"]:
                    relevance_score += 1

            if relevance_score > 0:
                relevant_docs.append((doc, relevance_score))

        # 按相關性排序
        relevant_docs.sort(key=lambda x: x[1], reverse=True)

        if relevant_docs:
            answer = "根據相關資料：\n\n"
            for doc, score in relevant_docs[:3]:
                answer += f"• {doc['title']}: {doc['content']}\n\n"
            return answer
        else:
            # 如果沒有特別相關的，就返回前幾個
            answer = "根據檢索到的相關資料：\n\n"
            for doc in documents[:2]:
                answer += f"• {doc['title']}: {doc['content']}\n\n"
            return answer
    
    def _format_sources(self, retrieved_docs: List[Dict]) -> List[Dict]:
        """格式化資料來源"""
        sources = []
        
        for doc in retrieved_docs:
            metadata = doc.get("metadata", {})
            source = {
                "title": metadata.get("title", "未知標題"),
                "url": metadata.get("url", ""),
                "source": metadata.get("source", "未知來源"),
                "score": doc.get("score", 0.0),
                "content_preview": doc.get("content", "")[:100] + "..."
            }
            sources.append(source)
        
        return sources
    
    def _get_search_suggestions(self) -> List[str]:
        """獲得搜尋建議"""
        return [
            "東吳大學",
            "校園活動",
            "學術研究",
            "人事異動",
            "國際合作",
            "學生事務"
        ]
    
    def batch_qa(self, questions: List[str], **kwargs) -> List[Dict[str, Any]]:
        """批量問答"""
        results = []
        
        for question in questions:
            result = self.answer_question(question, **kwargs)
            results.append(result)
        
        return results
