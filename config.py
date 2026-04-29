from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # 应用基本配置
    APP_NAME: str = "内部知识库系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 知识库存储路径
    KNOWLEDGE_BASE_PATH: str = Field(
        default="./knowledge_base",
        description="知识库文件存储路径"
    )

    # 向量数据库配置
    VECTOR_DB_PATH: str = Field(
        default="./vector_db",
        description="向量数据库存储路径"
    )

    VECTOR_DB_COLLECTION_NAME: str = Field(
        default="knowledge_base",
        description="向量数据库集合名称"
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
    SUPPORTED_FILE_TYPES: list = Field(
        default=["pdf", "txt", "md"],
        description="支持上传的文件类型"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


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