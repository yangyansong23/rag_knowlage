from typing import List, Optional, Dict, Any
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

from config import settings
from document_processor import document_processor


class RAGSystem:
    """RAG问答系统类"""
    
    def __init__(self):
        # 初始化LLM
        self.llm = self._init_llm()
        
        # 获取检索器
        self.retriever = document_processor.get_retriever()
        
        # 创建RAG链
        self.qa_chain = self._create_qa_chain()
    
    def _init_llm(self):
        """初始化LLM模型"""
        if settings.LLM_TYPE == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model_name=settings.LLM_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1
            )
        elif settings.LLM_TYPE == "local":
            # 使用简单的本地模拟或提示用户配置
            # 这里我们使用一个简单的实现，实际使用时可以替换为本地LLM
            # 对于初学者，我们先实现一个基于模板的简单回答
            # 实际部署时可以使用Ollama或其他本地模型
            return self._create_simple_llm()
        else:
            raise ValueError(f"不支持的LLM类型: {settings.LLM_TYPE}")
    
    def _create_simple_llm(self):
        """
        创建一个简单的LLM实现，用于演示
        实际使用时应该替换为真正的LLM
        """
        # 这里我们使用一个自定义的简单LLM类
        # 它将基于检索到的文档生成回答
        class SimpleLLM:
            def invoke(self, prompt):
                """简单的调用方法"""
                # 解析prompt，提取问题和上下文
                prompt_text = str(prompt)
                
                # 尝试从prompt中提取上下文和问题
                # 这是一个简单的实现，实际LLM会更智能
                try:
                    # 提取上下文部分
                    context_start = prompt_text.find("Context:")
                    question_start = prompt_text.find("Question:")
                    
                    if context_start != -1 and question_start != -1:
                        context = prompt_text[context_start + 8:question_start].strip()
                        question = prompt_text[question_start + 9:].strip()
                        
                        # 基于上下文生成简单回答
                        # 实际LLM会进行更复杂的推理
                        return SimpleLLMResult(
                            content=f"基于提供的上下文信息，关于'{question}'的回答如下：\n\n{context[:500]}..." if len(context) > 500 else f"基于提供的上下文信息，关于'{question}'的回答如下：\n\n{context}"
                        )
                except Exception:
                    pass
                
                return SimpleLLMResult(
                    content="抱歉，我目前无法处理您的问题。请确保已配置有效的LLM模型。"
                )
        
        class SimpleLLMResult:
            def __init__(self, content):
                self.content = content
        
        return SimpleLLM()
    
    def _create_qa_chain(self):
        """创建RAG问答链"""
        # 定义提示模板
        prompt_template = """
使用以下上下文来回答最后的问题。如果你不知道答案，就说你不知道，不要试图编造答案。

Context: {context}

Question: {question}

请给出详细的回答：
"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # 创建RAG链
        chain_type_kwargs = {"prompt": PROMPT}
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs=chain_type_kwargs
        )
        
        return qa_chain
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        执行RAG查询
        
        Args:
            question: 用户的问题
            
        Returns:
            包含回答和源文档的字典
        """
        # 执行查询
        result = self.qa_chain.invoke({"query": question})
        
        # 提取结果
        answer = result.get("result", "")
        source_documents = result.get("source_documents", [])
        
        # 准备响应
        response = {
            "question": question,
            "answer": answer,
            "sources": []
        }
        
        # 处理源文档
        for doc in source_documents:
            source_info = {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            response["sources"].append(source_info)
        
        return response
    
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
        
        # 搜索相关文档
        docs = document_processor.search(query, k=k)
        
        # 准备结果
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        return results
    
    def get_relevant_context(self, question: str) -> str:
        """
        获取与问题相关的上下文
        
        Args:
            question: 用户的问题
            
        Returns:
            相关上下文文本
        """
        # 搜索相关文档
        docs = document_processor.search(question)
        
        # 合并文档内容
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", f"文档 {i+1}")
            context_parts.append(f"[来源: {source}]\n{doc.page_content}\n")
        
        return "\n".join(context_parts)
    
    def refresh_chain(self):
        """
        刷新RAG链，当向量数据库更新后调用
        """
        self.retriever = document_processor.get_retriever()
        self.qa_chain = self._create_qa_chain()


# 创建全局RAG系统实例
rag_system = RAGSystem()
