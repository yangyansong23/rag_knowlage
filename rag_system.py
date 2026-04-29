from typing import List, Dict, Any, Optional
from document_processor import document_processor
from config import settings
from llm_service import llm_service


class SimpleRAGSystem:
    """
    简化的 RAG 问答系统
    支持使用 LLM 进行智能回答生成
    """

    def __init__(self):
        """初始化 RAG 系统"""
        print("RAG 问答系统初始化完成")
        print(f"  - 检索返回数量: {settings.RETRIEVER_TOP_K}")
        print(f"  - LLM 提供者: {settings.LLM_PROVIDER}")

    def query(self, question: str) -> Dict[str, Any]:
        """
        执行 RAG 查询

        Args:
            question: 用户的问题

        Returns:
            包含回答和参考资料的字典
        """
        # 1. 检索相关文档
        relevant_docs = document_processor.search(
            query=question,
            k=settings.RETRIEVER_TOP_K
        )

        # 2. 如果没有找到相关文档
        if not relevant_docs:
            return {
                "question": question,
                "answer": "抱歉，我在知识库中没有找到与您问题相关的信息。请先上传相关文档到知识库。",
                "sources": [],
                "llm_used": False
            }

        # 3. 准备上下文
        context = self._build_context(relevant_docs)

        # 4. 使用 LLM 生成回答
        try:
            answer = llm_service.generate_with_context(question, context)
            llm_used = True
        except Exception as e:
            print(f"LLM 生成回答失败: {e}，使用备用方案")
            answer = self._fallback_answer(question, relevant_docs)
            llm_used = False

        # 5. 准备响应
        response = {
            "question": question,
            "answer": answer,
            "sources": relevant_docs,
            "llm_used": llm_used,
            "llm_provider": llm_service.active_provider if hasattr(llm_service, 'active_provider') else None
        }

        return response

    def _build_context(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        构建上下文文本

        Args:
            relevant_docs: 相关文档列表

        Returns:
            合并后的上下文文本
        """
        context_parts = []

        for i, doc in enumerate(relevant_docs):
            source = doc["metadata"].get("source", f"文档 {i + 1}")
            content = doc["content"]

            context_parts.append(f"--- [来源: {source}] ---")
            context_parts.append(content)
            context_parts.append("")

        return "\n".join(context_parts)

    def _fallback_answer(self, question: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        备用回答生成（当 LLM 不可用时）

        Args:
            question: 用户问题
            relevant_docs: 相关文档列表

        Returns:
            备用回答
        """
        # 合并所有相关文档的内容
        all_content = "\n\n".join([doc["content"] for doc in relevant_docs])

        # 简单的回答生成逻辑
        if not all_content.strip():
            return "抱歉，没有找到足够的信息来回答您的问题。"

        answer_parts = []

        answer_parts.append("根据知识库中的相关信息，为您整理如下回答：\n")

        # 添加文档摘要
        for i, doc in enumerate(relevant_docs):
            source = doc["metadata"].get("source", f"文档 {i + 1}")
            content = doc["content"]

            # 截取部分内容
            preview = content[:300]
            if len(content) > 300:
                preview += "..."

            answer_parts.append(f"\n【来源: {source}】")
            answer_parts.append(preview)

        answer_parts.append("\n\n💡 提示：")
        answer_parts.append("- 以上信息来自知识库中检索到的相关文档片段")
        answer_parts.append("- 当前使用的是备用回答模式")
        answer_parts.append("- 如需更智能的回答，请配置 LLM 服务")

        return "\n".join(answer_parts)

    def search_documents(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        仅搜索相关文档，不生成回答

        Args:
            query: 查询文本
            k: 返回的文档数量

        Returns:
            相关文档列表
        """
        if k is None:
            k = settings.RETRIEVER_TOP_K

        return document_processor.search(query, k)

    def get_relevant_context(self, question: str) -> str:
        """
        获取与问题相关的上下文文本

        Args:
            question: 用户问题

        Returns:
            相关上下文文本
        """
        docs = document_processor.search(question)

        if not docs:
            return "没有找到相关的上下文信息。"

        return self._build_context(docs)

    def get_database_status(self) -> Dict[str, Any]:
        """
        获取数据库状态

        Returns:
            数据库状态信息
        """
        count = document_processor.get_document_count()

        return {
            "document_count": count,
            "collection_name": settings.VECTOR_DB_COLLECTION_NAME,
            "retriever_top_k": settings.RETRIEVER_TOP_K,
            "vector_db_type": settings.VECTOR_DB_TYPE
        }

    def get_llm_status(self) -> Dict[str, Any]:
        """
        获取 LLM 服务状态

        Returns:
            LLM 状态信息
        """
        return llm_service.get_status()


# 创建全局实例
rag_system = SimpleRAGSystem()
