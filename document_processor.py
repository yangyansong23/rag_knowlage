import os
import re
import math
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import settings
from vector_db import get_vector_db, VectorDBBase
from document_loaders import loader_factory


class DocumentProcessor:
    """
    文档处理器
    支持多种向量数据库
    """

    def __init__(self):
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )

        # 初始化向量数据库
        self.vector_db: VectorDBBase = get_vector_db()

        print(f"文档处理器初始化完成")
        print(f"  - 分块大小: {settings.CHUNK_SIZE}")
        print(f"  - 重叠大小: {settings.CHUNK_OVERLAP}")
        print(f"  - 向量数据库类型: {settings.VECTOR_DB_TYPE}")
        print(f"  - 向量数据库路径: {settings.VECTOR_DB_PATH}")

    def load_document(self, file_path: str) -> List[Document]:
        """
        加载单个文档

        Args:
            file_path: 文件路径

        Returns:
            文档列表
        """
        try:
            return loader_factory.load_document(file_path)
        except Exception as e:
            print(f"加载文档失败 {file_path}: {e}")
            raise

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        分割文档

        Args:
            documents: 文档列表

        Returns:
            分割后的文档列表
        """
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

        # 添加 source 元数据
        for metadata in metadatas:
            if "source" not in metadata:
                metadata["source"] = file_path

        # 添加到向量数据库
        self.vector_db.add_documents(
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
        count = self.vector_db.get_document_count()
        if count == 0:
            print("警告: 向量数据库为空，请先上传文档")
            return []

        # 执行搜索
        return self.vector_db.search(query, min(k, count))

    def get_document_count(self) -> int:
        """
        获取文档数量

        Returns:
            文档总数
        """
        return self.vector_db.get_document_count()

    def clear_database(self):
        """
        清空数据库
        """
        self.vector_db.clear()

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

        # 支持的文件扩展名（从文档加载器工厂获取）
        supported_extensions = set(loader_factory.get_supported_extensions())

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

    def get_vector_db_config(self) -> Dict[str, Any]:
        """
        获取向量数据库配置

        Returns:
            配置信息
        """
        return self.vector_db.get_config()


# 创建全局实例
document_processor = DocumentProcessor()
