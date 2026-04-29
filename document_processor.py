import os
from pathlib import Path
from typing import List, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from config import settings


class DocumentProcessor:
    """文档处理器类，负责文档加载、分块和向量化"""
    
    def __init__(self):
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # 初始化嵌入模型
        self.embeddings = self._init_embeddings()
        
        # 初始化向量存储
        self.vectorstore = self._init_vectorstore()
    
    def _init_embeddings(self):
        """初始化嵌入模型"""
        if settings.EMBEDDING_MODEL_TYPE == "local":
            # 使用本地HuggingFace模型
            return HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME
            )
        elif settings.EMBEDDING_MODEL_TYPE == "openai":
            # 使用OpenAI嵌入模型
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            raise ValueError(f"不支持的嵌入模型类型: {settings.EMBEDDING_MODEL_TYPE}")
    
    def _init_vectorstore(self):
        """初始化向量存储"""
        if settings.VECTOR_DB_TYPE == "chromadb":
            # 检查向量数据库是否已存在
            persist_directory = settings.VECTOR_DB_PATH
            collection_name = settings.VECTOR_DB_COLLECTION_NAME
            
            # 如果目录存在且有数据，加载现有数据库
            if os.path.exists(persist_directory) and os.listdir(persist_directory):
                return Chroma(
                    persist_directory=persist_directory,
                    embedding_function=self.embeddings,
                    collection_name=collection_name
                )
            else:
                # 创建新的向量数据库
                return Chroma(
                    persist_directory=persist_directory,
                    embedding_function=self.embeddings,
                    collection_name=collection_name
                )
        else:
            raise ValueError(f"不支持的向量数据库类型: {settings.VECTOR_DB_TYPE}")
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        加载单个文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            文档对象列表
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension in [".txt", ".md"]:
            loader = TextLoader(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_extension}")
        
        return loader.load()
    
    def load_directory(self, directory_path: str) -> List[Document]:
        """
        加载整个目录中的文档
        
        Args:
            directory_path: 目录路径
            
        Returns:
            文档对象列表
        """
        loader = DirectoryLoader(
            directory_path,
            glob="**/*.{pdf,txt,md}",
            show_progress=True
        )
        return loader.load()
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        将文档分割成小块
        
        Args:
            documents: 文档对象列表
            
        Returns:
            分块后的文档对象列表
        """
        return self.text_splitter.split_documents(documents)
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        将文档添加到向量数据库
        
        Args:
            documents: 文档对象列表
            
        Returns:
            添加的文档ID列表
        """
        # 先分割文档
        split_docs = self.split_documents(documents)
        
        # 添加到向量数据库
        ids = self.vectorstore.add_documents(split_docs)
        
        # 持久化（如果需要）
        if hasattr(self.vectorstore, 'persist'):
            self.vectorstore.persist()
        
        return ids
    
    def add_file(self, file_path: str) -> List[str]:
        """
        添加单个文件到知识库
        
        Args:
            file_path: 文件路径
            
        Returns:
            添加的文档ID列表
        """
        documents = self.load_document(file_path)
        return self.add_documents(documents)
    
    def add_directory(self, directory_path: str) -> List[str]:
        """
        添加整个目录到知识库
        
        Args:
            directory_path: 目录路径
            
        Returns:
            添加的文档ID列表
        """
        documents = self.load_directory(directory_path)
        return self.add_documents(documents)
    
    def search(self, query: str, k: int = None) -> List[Document]:
        """
        在知识库中搜索相关文档
        
        Args:
            query: 查询文本
            k: 返回的文档数量，默认使用配置中的值
            
        Returns:
            相关文档列表
        """
        if k is None:
            k = settings.RETRIEVER_TOP_K
        
        return self.vectorstore.similarity_search(query, k=k)
    
    def search_with_score(self, query: str, k: int = None) -> List[tuple]:
        """
        在知识库中搜索相关文档并返回相似度分数
        
        Args:
            query: 查询文本
            k: 返回的文档数量，默认使用配置中的值
            
        Returns:
            包含(文档, 分数)的元组列表
        """
        if k is None:
            k = settings.RETRIEVER_TOP_K
        
        return self.vectorstore.similarity_search_with_score(query, k=k)
    
    def get_retriever(self):
        """
        获取检索器对象，用于RAG链
        
        Returns:
            检索器对象
        """
        return self.vectorstore.as_retriever(
            search_kwargs={"k": settings.RETRIEVER_TOP_K}
        )
    
    def clear_database(self):
        """
        清空向量数据库
        """
        # 删除持久化目录
        if os.path.exists(settings.VECTOR_DB_PATH):
            import shutil
            shutil.rmtree(settings.VECTOR_DB_PATH)
        
        # 重新初始化向量存储
        self.vectorstore = self._init_vectorstore()


# 创建全局文档处理器实例
document_processor = DocumentProcessor()
