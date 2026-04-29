from typing import List, Dict, Any, Optional
from document_processor import document_processor
from config import settings


class SimpleRAGSystem:
    """
    简化的RAG问答系统
    不依赖复杂的LangChain链结构，直接实现基本的检索和回答逻辑
    """

    def __init__(self):
        """初始化RAG系统"""
        print("RAG问答系统初始化完成")
        print(f"  - 检索返回数量: {settings.RETRIEVER_TOP_K}")

    def query(self, question: str) -> Dict[str, Any]:
        """
        执行RAG查询

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
                "sources": []
            }

        # 3. 生成回答（简化版本，基于检索到的文档）
        # 实际生产环境可以替换为真正的LLM调用
        answer = self._generate_answer(question, relevant_docs)

        # 4. 准备响应
        response = {
            "question": question,
            "answer": answer,
            "sources": relevant_docs
        }

        return response

    def _generate_answer(self, question: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        基于检索到的文档生成回答

        这是一个简化版本，实际应用中应该使用LLM来生成更自然的回答。
        目前的实现：
        1. 合并相关文档内容
        2. 提供基于关键词匹配的简单回答

        Args:
            question: 用户问题
            relevant_docs: 相关文档列表

        Returns:
            生成的回答文本
        """
        # 合并所有相关文档的内容
        all_content = "\n\n".join([doc["content"] for doc in relevant_docs])

        # 简单的回答生成逻辑
        # 实际应用中应该调用LLM来生成更智能的回答

        # 检查是否有足够的内容
        if not all_content.strip():
            return "抱歉，没有找到足够的信息来回答您的问题。"

        # 生成回答（简化版本）
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
        answer_parts.append("- 您可以查看下方的参考资料获取完整内容")
        answer_parts.append("- 如需更智能的回答，请配置LLM（如OpenAI或本地模型）")

        # 检查是否可以配置更智能的回答
        answer_parts.append(f"\n\n📝 关于回答质量：")
        answer_parts.append(f"当前系统使用的是基于规则的简单回答生成。")
        answer_parts.append(f"如需获取更智能、更自然的回答，您可以：")
        answer_parts.append(f"  1. 配置OpenAI API（需要API密钥）")
        answer_parts.append(f"  2. 或集成本地LLM（如Ollama + Llama2）")

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

        context_parts = []
        for i, doc in enumerate(docs):
            source = doc["metadata"].get("source", f"文档 {i + 1}")
            context_parts.append(f"--- [来源: {source}] ---")
            context_parts.append(doc["content"])
            context_parts.append("")

        return "\n".join(context_parts)

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
            "retriever_top_k": settings.RETRIEVER_TOP_K
        }


# 创建全局实例
rag_system = SimpleRAGSystem()