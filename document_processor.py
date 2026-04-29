import os
import re
import math
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

# LangChain文档加载和分割
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# ChromaDB
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings


class SimpleEmbeddingFunction:
    """
    轻量级嵌入函数，基于TF-IDF和特征哈希
    完全兼容ChromaDB的EmbeddingFunction接口
    """

    def __init__(self, embedding_dim: int = 384):
        """
        初始化简单嵌入函数

        Args:
            embedding_dim: 嵌入向量维度，默认384
        """
        self.embedding_dim = embedding_dim
        self.idf: Dict[str, float] = {}
        self.doc_count = 0
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        text = text.lower()
        # 匹配中文、英文单词和数字
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text)
        return tokens

    def _get_ngrams(self, tokens: List[str], n: int = 2) -> List[str]:
        """生成n-gram特征"""
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = '_'.join(tokens[i:i + n])
            ngrams.append(ngram)
        return ngrams

    def fit(self, texts: List[str]):
        """训练IDF"""
        self.doc_count = len(texts)
        doc_freq: Dict[str, int] = {}

        for text in texts:
            tokens = self._tokenize(text)
            features = tokens + self._get_ngrams(tokens, 2)
            unique_features = set(features)

            for feature in unique_features:
                doc_freq[feature] = doc_freq.get(feature, 0) + 1

        # 计算IDF（平滑处理）
        for feature, freq in doc_freq.items():
            self.idf[feature] = math.log((self.doc_count + 1) / (freq + 1)) + 1

        self._fitted = True

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        ChromaDB要求的调用接口
        将文本列表转换为嵌入向量列表
        """
        # 如果还没训练，先用这些文本训练
        if not self._fitted and len(input) > 0:
            self.fit(input)

        return [self._embed_single(text) for text in input]

    def _embed_single(self, text: str) -> List[float]:
        """将单个文本转换为嵌入向量"""
        tokens = self._tokenize(text)
        features = tokens + self._get_ngrams(tokens, 2)

        # 统计词频
        tf = Counter(features)

        # 初始化向量
        vector = [0.0] * self.embedding_dim

        # 计算TF-IDF并哈希到向量
        for feature, count in tf.items():
            # 获取IDF值（默认1.0）
            idf_val = self.idf.get(feature, 1.0)
            tf_idf = count * idf_val

            # 特征哈希
            hash_val = hash(feature) % (self.embedding_dim * 10)
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


class DocumentProcessor:
    """简化的文档处理器"""

    def __init__(self):
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )

        # 初始化嵌入函数
        self.embedding_function = SimpleEmbeddingFunction(embedding_dim=384)

        # 初始化ChromaDB
        self._init_chroma()

        print(f"文档处理器初始化完成")
        print(f"  - 分块大小: {settings.CHUNK_SIZE}")
        print(f"  - 重叠大小: {settings.CHUNK_OVERLAP}")
        print(f"  - 向量数据库路径: {settings.VECTOR_DB_PATH}")

    def _init_chroma(self):
        """初始化ChromaDB"""
        # 确保目录存在
        db_path = Path(settings.VECTOR_DB_PATH)
        db_path.mkdir(parents=True, exist_ok=True)

        # 创建ChromaDB客户端
        self.chroma_client = chromadb.PersistentClient(
            path=str(db_path),
            settings=ChromaSettings(
                allow_reset=True,
                anonymized_telemetry=False  # 禁用遥测
            )
        )

        # 获取或创建集合
        collection_name = settings.VECTOR_DB_COLLECTION_NAME

        # 检查集合是否存在
        try:
            self.collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"已加载现有集合: {collection_name}")
        except Exception:
            # 创建新集合
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"已创建新集合: {collection_name}")

    def load_document(self, file_path: str) -> List[Document]:
        """加载单个文档"""
        file_extension = Path(file_path).suffix.lower()

        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
                return loader.load()
            elif file_extension in [".txt", ".md"]:
                loader = TextLoader(file_path)
                return loader.load()
            else:
                raise ValueError(f"不支持的文件类型: {file_extension}")
        except Exception as e:
            print(f"加载文档失败 {file_path}: {e}")
            raise

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """分割文档"""
        return self.text_splitter.split_documents(documents)

    def add_file(self, file_path: str) -> int:
        """
        添加单个文件到向量数据库

        Args:
            file_path: 文件路径

        Returns:
            添加的文档块数量
        """
        print(f"正在处理文件: {file_path}")

        # 加载文档
        documents = self.load_document(file_path)
        print(f"  加载了 {len(documents)} 个文档段")

        # 分割文档
        split_docs = self.split_documents(documents)
        print(f"  分割为 {len(split_docs)} 个文档块")

        if not split_docs:
            return 0

        # 准备数据
        texts = [doc.page_content for doc in split_docs]
        metadatas = [doc.metadata for doc in split_docs]

        # 添加source元数据
        for metadata in metadatas:
            if "source" not in metadata:
                metadata["source"] = file_path

        # 生成ID
        import uuid
        ids = [str(uuid.uuid4()) for _ in split_docs]

        # 添加到集合
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )

        print(f"  已添加到向量数据库")
        return len(split_docs)

    def search(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            相关文档列表
        """
        if k is None:
            k = settings.RETRIEVER_TOP_K

        # 检查集合是否为空
        count = self.collection.count()
        if count == 0:
            print("警告: 向量数据库为空，请先上传文档")
            return []

        # 执行搜索
        results = self.collection.query(
            query_texts=[query],
            n_results=min(k, count)
        )

        # 格式化结果
        formatted_results = []

        if results["documents"] and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None
                })

        return formatted_results

    def get_document_count(self) -> int:
        """获取文档数量"""
        return self.collection.count()

    def clear_database(self):
        """清空数据库"""
        collection_name = settings.VECTOR_DB_COLLECTION_NAME

        # 删除集合
        try:
            self.chroma_client.delete_collection(collection_name)
            print(f"已删除集合: {collection_name}")
        except Exception as e:
            print(f"删除集合时出错: {e}")

        # 重新创建集合
        self.collection = self.chroma_client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        print(f"已重新创建集合: {collection_name}")

    def rebuild_from_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        从目录重建数据库

        Args:
            directory_path: 目录路径

        Returns:
            重建结果统计
        """
        dir_path = Path(directory_path)

        if not dir_path.exists():
            return {
                "success": False,
                "message": f"目录不存在: {directory_path}"
            }

        # 清空数据库
        self.clear_database()

        # 统计
        total_files = 0
        total_chunks = 0
        errors = []

        # 支持的文件扩展名
        supported_extensions = {".pdf", ".txt", ".md"}

        # 遍历目录
        for file_path in dir_path.iterdir():
            if file_path.is_file():
                if file_path.suffix.lower() in supported_extensions:
                    try:
                        chunks = self.add_file(str(file_path))
                        total_files += 1
                        total_chunks += chunks
                    except Exception as e:
                        errors.append({
                            "file": file_path.name,
                            "error": str(e)
                        })

        return {
            "success": True,
            "total_files": total_files,
            "total_chunks": total_chunks,
            "errors": errors
        }


# 创建全局实例
document_processor = DocumentProcessor()