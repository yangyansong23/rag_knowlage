import os
import re
import math
import uuid
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

from config import settings


class VectorDBBase(ABC):
    """
    向量数据库基类
    定义统一的向量数据库接口
    """

    @abstractmethod
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        """
        添加文档到向量数据库

        Args:
            documents: 文档内容列表
            metadatas: 元数据列表（可选）
            ids: 文档 ID 列表（可选）

        Returns:
            添加的文档数量
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            相关文档列表，每个文档包含 content, metadata, distance
        """
        pass

    @abstractmethod
    def get_document_count(self) -> int:
        """
        获取文档数量

        Returns:
            文档总数
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        清空数据库
        """
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置

        Returns:
            配置信息字典
        """
        pass


class SimpleEmbeddingFunction:
    """
    轻量级嵌入函数，基于 TF-IDF 和特征哈希
    完全兼容各种向量数据库的嵌入接口
    """

    def __init__(self, embedding_dim: int = 384):
        """
        初始化简单嵌入函数

        Args:
            embedding_dim: 嵌入向量维度，默认 384
        """
        self.embedding_dim = embedding_dim
        self.idf: Dict[str, float] = {}
        self.doc_count = 0
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        text = text.lower()
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text)
        return tokens

    def _get_ngrams(self, tokens: List[str], n: int = 2) -> List[str]:
        """生成 n-gram 特征"""
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = '_'.join(tokens[i:i + n])
            ngrams.append(ngram)
        return ngrams

    def fit(self, texts: List[str]):
        """训练 IDF"""
        self.doc_count = len(texts)
        doc_freq: Dict[str, int] = {}

        for text in texts:
            tokens = self._tokenize(text)
            features = tokens + self._get_ngrams(tokens, 2)
            unique_features = set(features)

            for feature in unique_features:
                doc_freq[feature] = doc_freq.get(feature, 0) + 1

        for feature, freq in doc_freq.items():
            self.idf[feature] = math.log((self.doc_count + 1) / (freq + 1)) + 1

        self._fitted = True

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        将文本列表转换为嵌入向量列表

        Args:
            input: 文本列表

        Returns:
            嵌入向量列表
        """
        if not self._fitted and len(input) > 0:
            self.fit(input)

        return [self._embed_single(text) for text in input]

    def _embed_single(self, text: str) -> List[float]:
        """将单个文本转换为嵌入向量"""
        tokens = self._tokenize(text)
        features = tokens + self._get_ngrams(tokens, 2)

        tf = Counter(features)
        vector = [0.0] * self.embedding_dim

        for feature, count in tf.items():
            idf_val = self.idf.get(feature, 1.0)
            tf_idf = count * idf_val

            hash_val = hash(feature) % (self.embedding_dim * 10)
            sign = 1 if hash(feature + "_sign") % 2 == 0 else -1

            num_bins = min(5, self.embedding_dim)
            for i in range(num_bins):
                idx = (hash_val + i * 13) % self.embedding_dim
                vector[idx] += sign * tf_idf * (1.0 / (i + 1))

        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector


class ChromaDBVectorDB(VectorDBBase):
    """
    ChromaDB 向量数据库实现
    """

    def __init__(self):
        """初始化 ChromaDB"""
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.embedding_function = SimpleEmbeddingFunction(
            embedding_dim=settings.EMBEDDING_DIMENSION
        )

        db_path = Path(settings.VECTOR_DB_PATH)
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=ChromaSettings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )

        collection_name = settings.VECTOR_DB_COLLECTION_NAME

        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"✓ ChromaDB: 已加载现有集合: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            print(f"✓ ChromaDB: 已创建新集合: {collection_name}")

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        if not documents:
            return 0

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        count = self.get_document_count()
        if count == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(k, count)
        )

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
        return self.collection.count()

    def clear(self) -> None:
        collection_name = settings.VECTOR_DB_COLLECTION_NAME

        try:
            self.client.delete_collection(collection_name)
            print(f"✓ ChromaDB: 已删除集合: {collection_name}")
        except Exception as e:
            print(f"⚠ ChromaDB: 删除集合时出错: {e}")

        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        print(f"✓ ChromaDB: 已重新创建集合: {collection_name}")

    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "chroma",
            "path": settings.VECTOR_DB_PATH,
            "collection_name": settings.VECTOR_DB_COLLECTION_NAME,
            "embedding_dimension": settings.EMBEDDING_DIMENSION
        }


class FAISSVectorDB(VectorDBBase):
    """
    FAISS 向量数据库实现
    """

    def __init__(self):
        """初始化 FAISS"""
        try:
            import faiss
            import numpy as np
            self.faiss = faiss
            self.np = np
        except ImportError:
            raise ImportError(
                "FAISS 未安装。请运行: pip install faiss-cpu 或 pip install faiss-gpu"
            )

        self.embedding_function = SimpleEmbeddingFunction(
            embedding_dim=settings.EMBEDDING_DIMENSION
        )

        self.db_path = Path(settings.VECTOR_DB_PATH)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.index_path = self.db_path / "faiss_index.bin"
        self.metadata_path = self.db_path / "metadata.json"

        self.dimension = settings.EMBEDDING_DIMENSION
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.index: Any = None

        self._load_or_create_index()

        print(f"✓ FAISS: 初始化完成，维度: {self.dimension}")

    def _load_or_create_index(self):
        """加载或创建索引"""
        if self.index_path.exists():
            try:
                self.index = self.faiss.read_index(str(self.index_path))
                if self.metadata_path.exists():
                    import json
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.documents = data.get("documents", [])
                        self.metadatas = data.get("metadatas", [])
                print(f"✓ FAISS: 已加载现有索引，文档数: {len(self.documents)}")
                return
            except Exception as e:
                print(f"⚠ FAISS: 加载索引失败: {e}，创建新索引")

        self.index = self.faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self.metadatas = []

    def _save_index(self):
        """保存索引到磁盘"""
        self.faiss.write_index(self.index, str(self.index_path))

        import json
        metadata = {
            "documents": self.documents,
            "metadatas": self.metadatas
        }
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        if not documents:
            return 0

        if metadatas is None:
            metadatas = [{} for _ in documents]

        embeddings = self.embedding_function(documents)
        embeddings_np = self.np.array(embeddings).astype(self.np.float32)

        self.index.add(embeddings_np)

        self.documents.extend(documents)
        self.metadatas.extend(metadatas)

        self._save_index()

        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        if len(self.documents) == 0:
            return []

        query_embedding = self.embedding_function([query])[0]
        query_np = self.np.array([query_embedding]).astype(self.np.float32)

        k = min(k, len(self.documents))
        distances, indices = self.index.search(query_np, k)

        results = []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(self.documents):
                results.append({
                    "content": self.documents[idx],
                    "metadata": self.metadatas[idx] if idx < len(self.metadatas) else {},
                    "distance": float(distances[0][i])
                })

        return results

    def get_document_count(self) -> int:
        return len(self.documents)

    def clear(self) -> None:
        self.index = self.faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self.metadatas = []

        if self.index_path.exists():
            self.index_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()

        print("✓ FAISS: 数据库已清空")

    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "faiss",
            "path": str(self.db_path),
            "dimension": self.dimension,
            "index_type": "IndexFlatL2"
        }


class QdrantVectorDB(VectorDBBase):
    """
    Qdrant 向量数据库实现
    """

    def __init__(self):
        """初始化 Qdrant"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams
            self.QdrantClient = QdrantClient
            self.Distance = Distance
            self.VectorParams = VectorParams
        except ImportError:
            raise ImportError(
                "Qdrant 客户端未安装。请运行: pip install qdrant-client"
            )

        self.embedding_function = SimpleEmbeddingFunction(
            embedding_dim=settings.EMBEDDING_DIMENSION
        )

        host = settings.QDRANT_HOST
        port = settings.QDRANT_PORT
        api_key = settings.QDRANT_API_KEY or None
        collection_name = settings.VECTOR_DB_COLLECTION_NAME

        try:
            if api_key:
                self.client = self.QdrantClient(
                    host=host,
                    port=port,
                    api_key=api_key
                )
            else:
                self.client = self.QdrantClient(
                    host=host,
                    port=port
                )

            self.dimension = settings.EMBEDDING_DIMENSION
            self.collection_name = collection_name

            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=self.VectorParams(
                        size=self.dimension,
                        distance=self.Distance.COSINE
                    )
                )
                print(f"✓ Qdrant: 已创建集合: {collection_name}")
            else:
                print(f"✓ Qdrant: 已加载集合: {collection_name}")

        except Exception as e:
            print(f"⚠ Qdrant 连接失败: {e}")
            print("  请确保 Qdrant 服务已启动或检查配置")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        if not documents:
            return 0

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        for i, metadata in enumerate(metadatas):
            if "content" not in metadata:
                metadata["content"] = documents[i]

        embeddings = self.embedding_function(documents)

        from qdrant_client.http.models import PointStruct

        points = [
            PointStruct(
                id=ids[i],
                vector=embeddings[i],
                payload=metadatas[i]
            )
            for i in range(len(documents))
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_function([query])[0]

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k
        )

        formatted_results = []
        for result in results:
            payload = result.payload or {}
            content = payload.get("content", "")

            formatted_results.append({
                "content": content,
                "metadata:": {k: v for k, v in payload.items() if k != "content"},
                "distance": result.score
            })

        return formatted_results

    def get_document_count(self) -> int:
        try:
            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )
            return collection_info.points_count or 0
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"✓ Qdrant: 已删除集合: {self.collection_name}")

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=self.VectorParams(
                    size=self.dimension,
                    distance=self.Distance.COSINE
                )
            )
            print(f"✓ Qdrant: 已重新创建集合: {self.collection_name}")
        except Exception as e:
            print(f"⚠ Qdrant 清空失败: {e}")

    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "qdrant",
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
            "collection_name": self.collection_name,
            "dimension": self.dimension
        }


class PineconeVectorDB(VectorDBBase):
    """
    Pinecone 向量数据库实现（云服务）
    """

    def __init__(self):
        """初始化 Pinecone"""
        try:
            import pinecone
            self.pinecone = pinecone
        except ImportError:
            raise ImportError(
                "Pinecone 客户端未安装。请运行: pip install pinecone-client"
            )

        self.embedding_function = SimpleEmbeddingFunction(
            embedding_dim=settings.EMBEDDING_DIMENSION
        )

        api_key = settings.PINECONE_API_KEY
        environment = settings.PINECONE_ENVIRONMENT
        index_name = settings.PINECONE_INDEX_NAME

        if not api_key or not environment:
            raise ValueError(
                "Pinecone 配置不完整。请设置 PINECONE_API_KEY 和 PINECONE_ENVIRONMENT"
            )

        try:
            self.pinecone.init(
                api_key=api_key,
                environment=environment
            )

            self.index_name = index_name
            self.dimension = settings.EMBEDDING_DIMENSION

            existing_indexes = self.pinecone.list_indexes()

            if index_name not in existing_indexes:
                self.pinecone.create_index(
                    name=index_name,
                    dimension=self.dimension,
                    metric="cosine"
                )
                print(f"✓ Pinecone: 已创建索引: {index_name}")
            else:
                print(f"✓ Pinecone: 已加载索引: {index_name}")

            self.index = self.pinecone.Index(index_name)

        except Exception as e:
            print(f"⚠ Pinecone 连接失败: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> int:
        if not documents:
            return 0

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        for i, metadata in enumerate(metadatas):
            if "content" not in metadata:
                metadata["content"] = documents[i]

        embeddings = self.embedding_function(documents)

        vectors = [
            (ids[i], embeddings[i], metadatas[i])
            for i in range(len(documents))
        ]

        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)

        return len(documents)

    def search(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_function([query])[0]

        results = self.index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True
        )

        formatted_results = []
        for match in results.matches:
            metadata = match.metadata or {}
            content = metadata.get("content", "")

            formatted_results.append({
                "content": content,
                "metadata": {k: v for k, v in metadata.items() if k != "content"},
                "distance": match.score
            })

        return formatted_results

    def get_document_count(self) -> int:
        try:
            index_stats = self.index.describe_index_stats()
            return index_stats.total_vector_count
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self.pinecone.delete_index(self.index_name)
            print(f"✓ Pinecone: 已删除索引: {self.index_name}")

            self.pinecone.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine"
            )
            print(f"✓ Pinecone: 已重新创建索引: {self.index_name}")

            self.index = self.pinecone.Index(self.index_name)
        except Exception as e:
            print(f"⚠ Pinecone 清空失败: {e}")

    def get_config(self) -> Dict[str, Any]:
        return {
            "type": "pinecone",
            "environment": settings.PINECONE_ENVIRONMENT,
            "index_name": self.index_name,
            "dimension": self.dimension
        }


def create_vector_db() -> VectorDBBase:
    """
    根据配置创建向量数据库实例

    Returns:
        向量数据库实例
    """
    db_type = settings.VECTOR_DB_TYPE.lower()

    if db_type == "chroma":
        return ChromaDBVectorDB()
    elif db_type == "faiss":
        return FAISSVectorDB()
    elif db_type == "qdrant":
        return QdrantVectorDB()
    elif db_type == "pinecone":
        return PineconeVectorDB()
    else:
        print(f"⚠ 不支持的向量数据库类型: {db_type}，使用默认的 ChromaDB")
        return ChromaDBVectorDB()


vector_db = None


def get_vector_db() -> VectorDBBase:
    """
    获取向量数据库单例实例

    Returns:
        向量数据库实例
    """
    global vector_db
    if vector_db is None:
        vector_db = create_vector_db()
    return vector_db
