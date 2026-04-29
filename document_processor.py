import os
import re
import math
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import Counter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import settings


class SimpleEmbeddings(Embeddings):
    """
    轻量级嵌入模型，基于TF-IDF和n-gram统计
    不需要外部依赖，适合初学者快速上手
    """
    
    def __init__(self, embedding_dim: int = 384):
        """
        初始化简单嵌入模型
        
        Args:
            embedding_dim: 嵌入向量的维度，默认384（与常用的MiniLM模型相同）
        """
        self.embedding_dim = embedding_dim
        self.idf: Dict[str, float] = {}  # 逆文档频率
        self.doc_count = 0  # 文档计数
        self.vocab: Dict[str, int] = {}  # 词汇表
        self._hash_range = embedding_dim * 10  # 哈希范围
        
    def _tokenize(self, text: str) -> List[str]:
        """
        简单的分词函数
        
        Args:
            text: 输入文本
            
        Returns:
            分词后的列表
        """
        # 转换为小写并分割
        text = text.lower()
        # 匹配中文、英文单词和数字
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text)
        return tokens
    
    def _get_ngrams(self, tokens: List[str], n: int = 2) -> List[str]:
        """
        生成n-gram特征
        
        Args:
            tokens: 分词列表
            n: n-gram的n值
            
        Returns:
            n-gram特征列表
        """
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = '_'.join(tokens[i:i+n])
            ngrams.append(ngram)
        return ngrams
    
    def _hash_feature(self, feature: str) -> int:
        """
        将特征哈希到固定范围
        
        Args:
            feature: 特征字符串
            
        Returns:
            哈希索引
        """
        return hash(feature) % self._hash_range
    
    def fit(self, texts: List[str]):
        """
        训练IDF（逆文档频率）
        
        Args:
            texts: 文档列表
        """
        self.doc_count = len(texts)
        doc_freq: Dict[str, int] = {}
        
        for text in texts:
            tokens = self._tokenize(text)
            # 使用unigram和bigram
            features = tokens + self._get_ngrams(tokens, 2)
            # 去重
            unique_features = set(features)
            
            for feature in unique_features:
                doc_freq[feature] = doc_freq.get(feature, 0) + 1
        
        # 计算IDF
        for feature, freq in doc_freq.items():
            # 平滑处理
            self.idf[feature] = math.log((self.doc_count + 1) / (freq + 1)) + 1
    
    def _embed_text(self, text: str) -> List[float]:
        """
        将单个文本转换为嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        tokens = self._tokenize(text)
        features = tokens + self._get_ngrams(tokens, 2)
        
        # 统计词频
        tf = Counter(features)
        
        # 初始化向量
        vector = [0.0] * self.embedding_dim
        
        # 计算TF-IDF并哈希到向量
        for feature, count in tf.items():
            # 计算TF-IDF值
            idf_val = self.idf.get(feature, 1.0)  # 默认IDF为1.0
            tf_idf = count * idf_val
            
            # 哈希到多个维度（使用特征哈希技巧）
            hash_val = self._hash_feature(feature)
            # 简单的符号确定（为了更好的分布）
            sign = 1 if hash(feature + "_sign") % 2 == 0 else -1
            
            # 分布到多个维度
            num_bins = min(5, self.embedding_dim)
            for i in range(num_bins):
                idx = (hash_val + i * 13) % self.embedding_dim
                vector[idx] += sign * tf_idf * (1.0 / (i + 1))
        
        # L2归一化
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入多个文档（LangChain要求的方法）
        
        Args:
            texts: 文档列表
            
        Returns:
            嵌入向量列表
        """
        # 如果还没有训练IDF，先用这些文本训练
        if not self.idf:
            self.fit(texts)
        
        return [self._embed_text(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        嵌入查询文本（LangChain要求的方法）
        
        Args:
            text: 查询文本
            
        Returns:
            嵌入向量
        """
        return self._embed_text(text)


def get_embeddings():
    """
    获取嵌入模型实例，自动选择可用的最佳选项
    """
    # 首先尝试使用HuggingFace Embeddings（如果已安装）
    if settings.EMBEDDING_MODEL_TYPE == "huggingface":
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL_NAME
            )
        except ImportError:
            print("警告: 未安装sentence-transformers，使用轻量级嵌入模型")
            return SimpleEmbeddings()
    
    # 使用OpenAI Embeddings
    elif settings.EMBEDDING_MODEL_TYPE == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY
            )
        except ImportError:
            print("警告: 未安装langchain-openai，使用轻量级嵌入模型")
            return SimpleEmbeddings()
    
    # 默认使用轻量级嵌入模型
    else:
        return SimpleEmbeddings()


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
        print(f"正在初始化嵌入模型，类型: {settings.EMBEDDING_MODEL_TYPE}")
        embeddings = get_embeddings()
        print(f"嵌入模型初始化完成: {type(embeddings).__name__}")
        return embeddings
    
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
