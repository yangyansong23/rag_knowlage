from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from config import settings


class VectorDBType(str, Enum):
    CHROMA = "chroma"
    FAISS = "faiss"
    QDRANT = "qdrant"
    PINECONE = "pinecone"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"
    ELASTICSEARCH = "elasticsearch"
    PG_VECTOR = "pgvector"


class IndexType(str, Enum):
    FLAT = "flat"
    HNSW = "hnsw"
    IVFFLAT = "ivfflat"
    IVFSQ8 = "ivfsq8"
    IVFPQ = "ivfpq"


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "inner_product"
    DOT_PRODUCT = "dot_product"


class StorageMode(str, Enum):
    PERSISTENT = "persistent"
    IN_MEMORY = "in_memory"
    HYBRID = "hybrid"


@dataclass
class VectorDBConfig:
    db_type: VectorDBType = VectorDBType.CHROMA
    index_type: IndexType = IndexType.FLAT
    distance_metric: DistanceMetric = DistanceMetric.COSINE
    storage_mode: StorageMode = StorageMode.PERSISTENT
    embedding_dimension: int = 384
    batch_size: int = 32
    collection_name: str = "knowledge_base"

    persist_path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None
    environment: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 128
    ivf_nlist: int = 1024
    ivf_nprobe: int = 10

    extra_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_settings(cls) -> "VectorDBConfig":
        db_type = VectorDBType(settings.VECTOR_DB_TYPE.lower())

        index_type_str = settings.VECTOR_DB_INDEX_TYPE.lower()
        try:
            index_type = IndexType(index_type_str)
        except ValueError:
            index_type = IndexType.FLAT

        metric_str = settings.VECTOR_DB_DISTANCE_METRIC.lower()
        try:
            distance_metric = DistanceMetric(metric_str)
        except ValueError:
            distance_metric = DistanceMetric.COSINE

        storage_mode = (
            StorageMode.PERSISTENT if settings.VECTOR_DB_PERSIST else StorageMode.IN_MEMORY
        )

        config = cls(
            db_type=db_type,
            index_type=index_type,
            distance_metric=distance_metric,
            storage_mode=storage_mode,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            collection_name=settings.VECTOR_DB_COLLECTION_NAME,
            persist_path=settings.VECTOR_DB_PATH,
        )

        if db_type == VectorDBType.QDRANT:
            config.host = settings.QDRANT_HOST
            config.port = settings.QDRANT_PORT
            config.api_key = settings.QDRANT_API_KEY or None

        elif db_type == VectorDBType.PINECONE:
            config.api_key = settings.PINECONE_API_KEY or None
            config.environment = settings.PINECONE_ENVIRONMENT or None
            config.collection_name = settings.PINECONE_INDEX_NAME

        return config

    def to_dict(self) -> Dict[str, Any]:
        return {
            "db_type": self.db_type.value,
            "index_type": self.index_type.value,
            "distance_metric": self.distance_metric.value,
            "storage_mode": self.storage_mode.value,
            "embedding_dimension": self.embedding_dimension,
            "batch_size": self.batch_size,
            "collection_name": self.collection_name,
            "persist_path": self.persist_path,
            "host": self.host,
            "port": self.port,
            "hnsw_m": self.hnsw_m,
            "hnsw_ef_construction": self.hnsw_ef_construction,
            "hnsw_ef_search": self.hnsw_ef_search,
            "ivf_nlist": self.ivf_nlist,
            "ivf_nprobe": self.ivf_nprobe,
            **self.extra_params,
        }

    def validate(self) -> Tuple[bool, List[str]]:
        errors = []

        if self.db_type in [VectorDBType.QDRANT, VectorDBType.MILVUS, VectorDBType.WEAVIATE]:
            if not self.host:
                errors.append(f"{self.db_type.value} 需要配置 host")
            if not self.port:
                errors.append(f"{self.db_type.value} 需要配置 port")

        if self.db_type == VectorDBType.PINECONE:
            if not self.api_key:
                errors.append("pinecone 需要配置 api_key")
            if not self.environment:
                errors.append("pinecone 需要配置 environment")

        if self.index_type == IndexType.HNSW:
            if self.hnsw_m <= 0:
                errors.append("hnsw_m 必须大于 0")
            if self.hnsw_ef_construction <= 0:
                errors.append("hnsw_ef_construction 必须大于 0")
            if self.hnsw_ef_search <= 0:
                errors.append("hnsw_ef_search 必须大于 0")

        if self.index_type in [IndexType.IVFFLAT, IndexType.IVFSQ8, IndexType.IVFPQ]:
            if self.ivf_nlist <= 0:
                errors.append("ivf_nlist 必须大于 0")
            if self.ivf_nprobe <= 0:
                errors.append("ivf_nprobe 必须大于 0")

        if self.embedding_dimension <= 0:
            errors.append("embedding_dimension 必须大于 0")

        if self.batch_size <= 0:
            errors.append("batch_size 必须大于 0")

        return len(errors) == 0, errors


def get_default_config(db_type: str) -> Dict[str, Any]:
    configs = {
        "chroma": {
            "description": "ChromaDB - 本地文件存储，零配置即用",
            "required_fields": ["persist_path", "collection_name"],
            "optional_fields": [],
            "index_types": ["flat", "hnsw"],
            "distance_metrics": ["cosine", "l2", "inner_product"],
            "default_index": "flat",
            "default_metric": "cosine",
        },
        "faiss": {
            "description": "FAISS - 高性能向量检索库",
            "required_fields": ["persist_path"],
            "optional_fields": [],
            "index_types": ["flat", "ivfflat", "ivfsq8", "ivfpq", "hnsw"],
            "distance_metrics": ["l2", "inner_product", "cosine"],
            "default_index": "flat",
            "default_metric": "l2",
        },
        "qdrant": {
            "description": "Qdrant - 开源向量数据库",
            "required_fields": ["host", "port", "collection_name"],
            "optional_fields": ["api_key"],
            "index_types": ["flat", "hnsw"],
            "distance_metrics": ["cosine", "l2", "dot_product"],
            "default_index": "hnsw",
            "default_metric": "cosine",
            "default_host": "localhost",
            "default_port": 6333,
        },
        "pinecone": {
            "description": "Pinecone - 云原生向量数据库",
            "required_fields": ["api_key", "environment", "index_name"],
            "optional_fields": [],
            "index_types": ["hnsw"],
            "distance_metrics": ["cosine", "l2", "dot_product"],
            "default_index": "hnsw",
            "default_metric": "cosine",
        },
        "milvus": {
            "description": "Milvus - 开源向量数据库",
            "required_fields": ["host", "port", "collection_name"],
            "optional_fields": ["username", "password", "database"],
            "index_types": ["flat", "hnsw", "ivfflat", "ivfsq8", "ivfpq"],
            "distance_metrics": ["l2", "inner_product", "cosine"],
            "default_index": "hnsw",
            "default_metric": "l2",
            "default_host": "localhost",
            "default_port": 19530,
        },
        "weaviate": {
            "description": "Weaviate - 开源向量数据库",
            "required_fields": ["host", "port"],
            "optional_fields": ["api_key"],
            "index_types": ["flat", "hnsw"],
            "distance_metrics": ["cosine", "l2", "dot_product"],
            "default_index": "hnsw",
            "default_metric": "cosine",
            "default_host": "localhost",
            "default_port": 8080,
        },
        "pgvector": {
            "description": "PGVector - PostgreSQL 扩展",
            "required_fields": ["host", "port", "database", "username", "password"],
            "optional_fields": [],
            "index_types": ["flat", "hnsw", "ivfflat"],
            "distance_metrics": ["cosine", "l2", "inner_product"],
            "default_index": "hnsw",
            "default_metric": "cosine",
            "default_host": "localhost",
            "default_port": 5432,
        },
    }

    return configs.get(db_type, configs["chroma"])


def get_available_vector_dbs() -> List[str]:
    return ["chroma", "faiss", "qdrant", "pinecone", "milvus", "weaviate", "pgvector"]


def get_index_type_description(index_type: str) -> str:
    descriptions = {
        "flat": "暴力搜索 - 100% 召回率，适合小规模数据",
        "hnsw": "分层导航小世界图 - 高召回率，高性能，内存占用较高",
        "ivfflat": "倒排文件 + 暴力搜索 - 平衡性能和召回率",
        "ivfsq8": "倒排文件 + 标量量化 - 高性能，内存占用低",
        "ivfpq": "倒排文件 + 乘积量化 - 极高压缩率，适合大规模数据",
    }
    return descriptions.get(index_type, index_type)


def get_distance_metric_description(metric: str) -> str:
    descriptions = {
        "cosine": "余弦相似度 - 适合文本相似度计算，不受向量长度影响",
        "l2": "欧几里得距离 - 适合空间坐标，受向量长度影响",
        "inner_product": "内积 - 与余弦相似度类似，但受向量长度影响",
        "dot_product": "点积 - 同内积",
    }
    return descriptions.get(metric, metric)
