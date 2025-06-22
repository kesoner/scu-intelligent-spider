#!/usr/bin/env python3
"""
簡化的 RAG 處理器

支援基於檢索資料的直接回答和 LLM 增強回答
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .vector_processor import VectorProcessor

# 檢查 Gemini 可用性
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI 套件未安裝，將使用基於檢索的回答")

# 檢查本地模型可用性
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    LOCAL_LLM_AVAILABLE = True
except ImportError:
    LOCAL_LLM_AVAILABLE = False
    logger.warning("Transformers 套件未安裝，將使用基於檢索的回答")


class SimpleRAGProcessor:
    """簡化的 RAG 處理器類別"""

    def __init__(self, config, use_llm: str = "none"):
        """
        初始化簡化 RAG 處理器

        Args:
            config: 配置管理器
            use_llm: 使用的 LLM 類型 ("none", "gemini", "local")
        """
        self.config = config
        self.vector_processor = VectorProcessor(config)
        self.use_llm = use_llm
        self.llm = None

        # 初始化 LLM
        if use_llm == "gemini" and GEMINI_AVAILABLE:
            self._init_gemini_llm()
        elif use_llm == "local" and LOCAL_LLM_AVAILABLE:
            self._init_local_llm()
        elif use_llm != "none":
            logger.warning(f"LLM 類型 '{use_llm}' 不可用，將使用基於檢索的回答")
            self.use_llm = "none"

        logger.info(f"簡化 RAG 處理器初始化完成，LLM 模式: {self.use_llm}")

    def _init_gemini_llm(self):
        """初始化 Gemini LLM"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("未找到 GEMINI_API_KEY 環境變數")
                self.use_llm = "none"
                return

            # 配置 Gemini
            genai.configure(api_key=api_key)

            # 初始化模型
            self.llm = genai.GenerativeModel('gemini-1.5-flash')

            # 測試連接
            test_response = self.llm.generate_content("測試")
            logger.info("Gemini LLM 初始化完成")
        except Exception as e:
            logger.error(f"Gemini LLM 初始化失敗: {e}")
            self.use_llm = "none"

    def _init_local_llm(self):
        """初始化本地 LLM"""
        try:
            # 使用較小的中文模型
            model_name = "microsoft/DialoGPT-medium"

            # 檢查是否有 GPU
            device = "cuda" if torch.cuda.is_available() else "cpu"

            # 載入模型
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)

            if device == "cuda":
                self.model = self.model.to(device)

            # 設定 pad_token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.llm = "local_model"
            logger.info(f"本地 LLM 初始化完成，使用設備: {device}")
        except Exception as e:
            logger.error(f"本地 LLM 初始化失敗: {e}")
            self.use_llm = "none"
    
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

            # 3. 生成答案（使用 LLM 或基於檢索）
            if self.use_llm != "none" and self.llm:
                answer = self._generate_llm_answer(question, retrieved_docs)
                model_type = f"llm_{self.use_llm}"
            else:
                answer = self._generate_retrieval_answer(question, retrieved_docs)
                model_type = "retrieval_based"

            # 4. 整理回應
            response = {
                "success": True,
                "question": question,
                "answer": answer,
                "sources": self._format_sources(retrieved_docs),
                "retrieved_count": len(retrieved_docs),
                "model_type": model_type
            }

            logger.info(f"問題回答完成，檢索到 {len(retrieved_docs)} 個相關文件，使用模型: {model_type}")
            return response

        except Exception as e:
            logger.error(f"回答問題時發生錯誤: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question
            }
    
    def _generate_llm_answer(self, question: str, retrieved_docs: List[Dict]) -> str:
        """使用 LLM 生成答案"""
        try:
            # 準備上下文
            context = self._prepare_context_for_llm(retrieved_docs)

            if self.use_llm == "gemini":
                return self._generate_gemini_answer(question, context)
            elif self.use_llm == "local":
                return self._generate_local_answer(question, context)
            else:
                # 回退到基於檢索的回答
                return self._generate_retrieval_answer(question, retrieved_docs)
        except Exception as e:
            logger.error(f"LLM 生成答案失敗: {e}")
            # 回退到基於檢索的回答
            return self._generate_retrieval_answer(question, retrieved_docs)

    def _generate_gemini_answer(self, question: str, context: str) -> str:
        """使用 Gemini 生成答案"""
        try:
            prompt = f"""你是東吳大學的智能助理，專門回答關於東吳大學的問題。請基於提供的資料給出準確、有用的回答。

請根據以下資料回答問題，使用繁體中文回答：

問題: {question}

相關資料:
{context}

請提供準確、詳細的回答。如果資料不足以完全回答問題，請說明並建議如何獲得更多資訊。
回答要求：
1. 直接回答問題
2. 基於提供的資料
3. 語言自然流暢
4. 如果有多個要點，請分點說明
5. 保持回答簡潔但完整
"""

            response = self.llm.generate_content(prompt)

            if response.text:
                return response.text.strip()
            else:
                logger.warning("Gemini 回應為空")
                return "抱歉，我無法基於提供的資料生成合適的回答。"

        except Exception as e:
            logger.error(f"Gemini 生成答案失敗: {e}")
            raise

    def _generate_local_answer(self, question: str, context: str) -> str:
        """使用本地模型生成答案"""
        try:
            # 簡化的提示詞，適合較小的模型
            prompt = f"問題: {question}\n資料: {context[:500]}...\n回答:"

            # 編碼輸入
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)

            # 生成回答
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 150,
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # 解碼回答
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 提取回答部分
            if "回答:" in generated_text:
                answer = generated_text.split("回答:")[-1].strip()
            else:
                answer = generated_text[len(prompt):].strip()

            return answer if answer else "抱歉，我無法基於提供的資料生成合適的回答。"

        except Exception as e:
            logger.error(f"本地模型生成答案失敗: {e}")
            raise

    def _prepare_context_for_llm(self, retrieved_docs: List[Dict]) -> str:
        """為 LLM 準備上下文"""
        context_parts = []

        for i, doc in enumerate(retrieved_docs[:5], 1):  # 限制前5個最相關的
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            title = metadata.get("title", f"文件 {i}")
            source = metadata.get("source", "未知來源")

            context_parts.append(f"文件 {i} (來源: {source}):\n標題: {title}\n內容: {content}\n")

        return "\n".join(context_parts)

    def _generate_retrieval_answer(self, question: str, retrieved_docs: List[Dict]) -> str:
        """基於檢索文件生成答案"""

        # 根據問題類型生成不同的回答
        if any(keyword in question for keyword in ["什麼", "是什麼", "哪些", "有什麼"]):
            return self._answer_what_question(question, retrieved_docs)
        elif any(keyword in question for keyword in ["如何", "怎麼", "怎樣"]):
            return self._answer_how_question(question, retrieved_docs)
        elif any(keyword in question for keyword in ["何時", "什麼時候", "時間"]):
            return self._answer_when_question(question, retrieved_docs)
        elif any(keyword in question for keyword in ["在哪", "哪裡", "地點"]):
            return self._answer_where_question(question, retrieved_docs)
        else:
            return self._answer_general_question(question, retrieved_docs)
    
    def _answer_what_question(self, question: str, docs: List[Dict]) -> str:
        """回答 '什麼' 類型的問題"""
        answer_parts = []
        
        # 檢查是否詢問特定主題
        if "認證" in question:
            for doc in docs:
                content = doc.get("content", "")
                if "認證" in content or "AACSB" in content:
                    title = doc.get("metadata", {}).get("title", "相關資料")
                    answer_parts.append(f"**{title}**\n{content}")
        elif "合作" in question or "國際" in question:
            for doc in docs:
                content = doc.get("content", "")
                if "合作" in content or "國際" in content:
                    title = doc.get("metadata", {}).get("title", "相關資料")
                    answer_parts.append(f"**{title}**\n{content}")
        elif "特色" in question:
            for doc in docs:
                content = doc.get("content", "")
                if any(keyword in content for keyword in ["特色", "優勢", "亮點", "成就"]):
                    title = doc.get("metadata", {}).get("title", "相關資料")
                    answer_parts.append(f"**{title}**\n{content}")
        else:
            # 一般性回答，顯示最相關的文件
            for doc in docs[:3]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer_parts.append(f"**{title}**\n{content}")
        
        if answer_parts:
            return "根據相關資料：\n\n" + "\n\n".join(answer_parts)
        else:
            return "根據檢索到的資料，我找到了相關內容，但沒有直接回答您問題的具體資訊。"
    
    def _answer_how_question(self, question: str, docs: List[Dict]) -> str:
        """回答 '如何' 類型的問題"""
        relevant_docs = []
        
        for doc in docs:
            content = doc.get("content", "")
            if any(keyword in content for keyword in ["申請", "步驟", "方法", "流程", "程序", "如何"]):
                relevant_docs.append(doc)
        
        if relevant_docs:
            answer = "關於您詢問的方法，根據相關資料：\n\n"
            for doc in relevant_docs[:2]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer += f"**{title}**\n{content}\n\n"
            return answer
        else:
            return "抱歉，在檢索到的資料中沒有找到具體的操作方法。建議您聯繫相關部門獲得詳細指導。"
    
    def _answer_when_question(self, question: str, docs: List[Dict]) -> str:
        """回答 '何時' 類型的問題"""
        time_related_docs = []
        
        for doc in docs:
            content = doc.get("content", "")
            if any(keyword in content for keyword in ["時間", "日期", "期間", "截止", "開始", "何時"]):
                time_related_docs.append(doc)
        
        if time_related_docs:
            answer = "關於時間資訊，根據相關資料：\n\n"
            for doc in time_related_docs[:2]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer += f"**{title}**\n{content}\n\n"
            return answer
        else:
            return "在檢索到的資料中沒有找到具體的時間資訊。建議查看最新的官方公告。"
    
    def _answer_where_question(self, question: str, docs: List[Dict]) -> str:
        """回答 '在哪' 類型的問題"""
        location_docs = []
        
        for doc in docs:
            content = doc.get("content", "")
            if any(keyword in content for keyword in ["地點", "位置", "地址", "校區", "辦公室", "在哪"]):
                location_docs.append(doc)
        
        if location_docs:
            answer = "關於地點資訊，根據相關資料：\n\n"
            for doc in location_docs[:2]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer += f"**{title}**\n{content}\n\n"
            return answer
        else:
            return "在檢索到的資料中沒有找到具體的地點資訊。建議聯繫相關部門確認。"
    
    def _answer_general_question(self, question: str, docs: List[Dict]) -> str:
        """回答一般性問題"""
        # 根據問題關鍵字找最相關的文件
        relevant_docs = []
        
        # 提取問題中的關鍵字
        keywords = []
        for word in question.split():
            if len(word) > 1 and word not in ["東吳", "大學", "的", "是", "有", "在", "和", "與", "？", "嗎"]:
                keywords.append(word)
        
        # 找包含關鍵字的文件
        for doc in docs:
            content = doc.get("content", "")
            title = doc.get("metadata", {}).get("title", "")
            relevance_score = 0
            
            for keyword in keywords:
                if keyword in content or keyword in title:
                    relevance_score += 1
            
            if relevance_score > 0:
                relevant_docs.append((doc, relevance_score))
        
        # 按相關性排序
        relevant_docs.sort(key=lambda x: x[1], reverse=True)
        
        if relevant_docs:
            answer = "根據相關資料：\n\n"
            for doc, score in relevant_docs[:3]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer += f"**{title}**\n{content}\n\n"
            return answer
        else:
            # 如果沒有特別相關的，就返回前幾個最相似的
            answer = "根據檢索到的相關資料：\n\n"
            for doc in docs[:2]:
                content = doc.get("content", "")
                title = doc.get("metadata", {}).get("title", "相關資料")
                answer += f"**{title}**\n{content}\n\n"
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
            "東吳大學商學院認證",
            "東吳大學國際合作",
            "東吳大學學生活動",
            "東吳大學人事異動",
            "東吳大學研究成果",
            "東吳大學校友表現"
        ]
    
    def batch_qa(self, questions: List[str], **kwargs) -> List[Dict[str, Any]]:
        """批量問答"""
        results = []
        
        for question in questions:
            result = self.answer_question(question, **kwargs)
            results.append(result)
        
        return results
