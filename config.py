import os
from pathlib import Path
from typing import Optional
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
    VECTOR_DB_TYPE: str = Field(
        default="chromadb",
        description="向量数据库类型，目前支持chromadb"
    )
    
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
        default=1000,
        description="文档分块大小"
    )
    
    CHUNK_OVERLAP: int = Field(
        default=200,
        description="文档分块重叠大小"
    )
    
    # 嵌入模型配置
    EMBEDDING_MODEL_TYPE: str = Field(
        default="local",
        description="嵌入模型类型：local或openai"
    )
    
    EMBEDDING_MODEL_NAME: str = Field(
        default="all-MiniLM-L6-v2",
        description="嵌入模型名称"
    )
    
    # LLM配置
    LLM_TYPE: str = Field(
        default="local",
        description="LLM类型：local或openai"
    )
    
    LLM_MODEL_NAME: str = Field(
        default="gpt-3.5-turbo",
        description="LLM模型名称"
    )
    
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API密钥"
    )
    
    # RAG配置
    RETRIEVER_TOP_K: int = Field(
        default=3,
        description="检索器返回的相关文档数量"
    )
    
    # 支持的文件类型
    SUPPORTED_FILE_TYPES: list = Field(
        default=["pdf", "txt", "md", "docx"],
        description="支持上传的文件类型"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建设置实例
settings = Settings()

# 确保必要的目录存在
def ensure_directories():
    """确保必要的目录存在"""
    # 创建知识库存储目录
    kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
    kb_path.mkdir(parents=True, exist_ok=True)
    
    # 创建向量数据库目录
    vectordb_path = Path(settings.VECTOR_DB_PATH)
    vectordb_path.mkdir(parents=True, exist_ok=True)
