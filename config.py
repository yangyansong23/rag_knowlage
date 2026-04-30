from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, Any, List


class Settings(BaseSettings):
    # 应用基本配置
    APP_NAME: str = "内部知识库系统"
    APP_VERSION: str = "2.1.0"
    DEBUG: bool = True

    # 服务器配置
    SERVER_HOST: str = Field(
        default="0.0.0.0",
        description="服务器监听地址"
    )

    SERVER_PORT: int = Field(
        default=8000,
        description="服务器端口"
    )

    PORT_RETRY_MAX: int = Field(
        default=10,
        description="端口占用时最大重试次数"
    )

    PORT_AUTO_FIND: bool = Field(
        default=True,
        description="是否自动查找可用端口"
    )

    # 知识库存储路径
    KNOWLEDGE_BASE_PATH: str = Field(
        default="./knowledge_base",
        description="知识库文件存储路径"
    )

    # 向量数据库配置
    VECTOR_DB_TYPE: str = Field(
        default="chroma",
        description="向量数据库类型: chroma, faiss, qdrant, pinecone"
    )

    VECTOR_DB_PATH: str = Field(
        default="./vector_db",
        description="向量数据库存储路径"
    )

    VECTOR_DB_COLLECTION_NAME: str = Field(
        default="knowledge_base",
        description="向量数据库集合名称"
    )

    # Qdrant 配置
    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant 主机地址"
    )

    QDRANT_PORT: int = Field(
        default=6333,
        description="Qdrant 端口"
    )

    QDRANT_API_KEY: str = Field(
        default="",
        description="Qdrant API 密钥（可选）"
    )

    # Pinecone 配置
    PINECONE_API_KEY: str = Field(
        default="",
        description="Pinecone API 密钥"
    )

    PINECONE_ENVIRONMENT: str = Field(
        default="",
        description="Pinecone 环境"
    )

    PINECONE_INDEX_NAME: str = Field(
        default="knowledge-base",
        description="Pinecone 索引名称"
    )

    # 嵌入模型配置
    EMBEDDING_TYPE: str = Field(
        default="simple",
        description="嵌入类型: simple, sentence_transformers, openai"
    )

    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="嵌入模型名称"
    )

    EMBEDDING_DIMENSION: int = Field(
        default=384,
        description="嵌入向量维度"
    )

    # 文档处理配置
    CHUNK_SIZE: int = Field(
        default=800,
        description="文档分块大小"
    )

    CHUNK_OVERLAP: int = Field(
        default=150,
        description="文档分块重叠大小"
    )

    # RAG配置
    RETRIEVER_TOP_K: int = Field(
        default=3,
        description="检索器返回的相关文档数量"
    )

    # 支持的文件类型
    SUPPORTED_FILE_TYPES: List[str] = Field(
        default=["pdf", "txt", "md", "doc", "docx", "xls", "xlsx", "ppt", "pptx"],
        description="支持上传的文件类型"
    )

    # 嵌入模型配置（扩展）
    EMBEDDING_PROVIDER: str = Field(
        default="simple",
        description="嵌入提供者类型: simple, openai, huggingface, ollama"
    )

    EMBEDDING_BATCH_SIZE: int = Field(
        default=32,
        description="嵌入处理批量大小"
    )

    # 向量数据库高级配置
    VECTOR_DB_PERSIST: bool = Field(
        default=True,
        description="向量数据库是否持久化存储"
    )

    VECTOR_DB_INDEX_TYPE: str = Field(
        default="flat",
        description="向量索引类型: flat, hnsw, ivfflat"
    )

    VECTOR_DB_DISTANCE_METRIC: str = Field(
        default="cosine",
        description="距离度量方式: cosine, l2, inner_product"
    )

    # LLM 配置
    LLM_PROVIDER: str = Field(
        default="rule_based",
        description="LLM 提供者类型: ollama, openai, generic, rule_based"
    )

    # Ollama 配置
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama 服务地址"
    )

    OLLAMA_MODEL: str = Field(
        default="llama2",
        description="Ollama 模型名称"
    )

    # OpenAI 配置
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API 密钥"
    )

    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API 基础地址"
    )

    OPENAI_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI 模型名称"
    )

    OPENAI_TEMPERATURE: float = Field(
        default=0.7,
        description="生成温度 (0.0-2.0)"
    )

    OPENAI_MAX_TOKENS: int = Field(
        default=2000,
        description="最大生成 Token 数"
    )

    # 通用 API 配置
    GENERIC_API_URL: str = Field(
        default="",
        description="通用 API 端点 URL"
    )

    GENERIC_API_KEY: str = Field(
        default="",
        description="通用 API 密钥（可选）"
    )

    GENERIC_API_MODEL: str = Field(
        default="",
        description="通用 API 模型名称（可选）"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# 创建设置实例
settings = Settings()


def ensure_directories():
    """确保必要的目录存在"""
    # 创建知识库存储目录
    kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
    kb_path.mkdir(parents=True, exist_ok=True)

    # 创建向量数据库目录
    vectordb_path = Path(settings.VECTOR_DB_PATH)
    vectordb_path.mkdir(parents=True, exist_ok=True)