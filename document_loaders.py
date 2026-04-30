from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Type
from langchain_core.documents import Document


class BaseDocumentLoader(ABC):
    """
    文档加载器基类
    定义统一的文档加载接口
    """

    @abstractmethod
    def load(self, file_path: str) -> List[Document]:
        """
        加载文档

        Args:
            file_path: 文件路径

        Returns:
            文档列表
        """
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名

        Returns:
            支持的扩展名列表（带点号，如 ['.pdf', '.txt']）
        """
        pass


class PDFLoader(BaseDocumentLoader):
    """
    PDF 文档加载器
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    def load(self, file_path: str) -> List[Document]:
        from langchain_community.document_loaders import PyPDFLoader

        loader = PyPDFLoader(file_path)
        return loader.load()


class TextLoader(BaseDocumentLoader):
    """
    纯文本文档加载器
    支持 .txt, .md, .markdown 等
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".txt", ".md", ".markdown", ".rst", ".log"]

    def load(self, file_path: str) -> List[Document]:
        from langchain_community.document_loaders import TextLoader

        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()


class WordLoader(BaseDocumentLoader):
    """
    Word 文档加载器
    支持 .doc, .docx
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".doc", ".docx"]

    def load(self, file_path: str) -> List[Document]:
        try:
            from langchain_community.document_loaders import Docx2txtLoader

            loader = Docx2txtLoader(file_path)
            return loader.load()
        except ImportError:
            return self._fallback_load(file_path)

    def _fallback_load(self, file_path: str) -> List[Document]:
        """
        备选加载方式：使用 python-docx 直接读取
        """
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(file_path)
            full_text = []

            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)

            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text)
                    full_text.append(" | ".join(row_text))

            content = "\n".join(full_text)

            return [
                Document(
                    page_content=content,
                    metadata={"source": file_path, "file_type": "word"}
                )
            ]
        except ImportError:
            raise ImportError(
                "Word 文档加载需要安装 python-docx 库。请运行: pip install python-docx"
            )


class ExcelLoader(BaseDocumentLoader):
    """
    Excel 文档加载器
    支持 .xls, .xlsx, .xlsm
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".xls", ".xlsx", ".xlsm", ".xlsb", ".csv"]

    def load(self, file_path: str) -> List[Document]:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Excel 文档加载需要安装 pandas 库。请运行: pip install pandas openpyxl xlrd"
            )

        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".csv":
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="gbk")
        elif file_extension == ".xls":
            try:
                df = pd.read_excel(file_path, engine="xlrd")
            except Exception:
                df = pd.read_excel(file_path)
        else:
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
            except Exception:
                df = pd.read_excel(file_path)

        documents = []

        for sheet_name in df.keys() if hasattr(df, 'keys') else [None]:
            if sheet_name:
                sheet_df = df[sheet_name]
            else:
                sheet_df = df

            for idx, row in sheet_df.iterrows():
                row_text_parts = []

                for col_name, value in row.items():
                    if pd.notna(value):
                        row_text_parts.append(f"{col_name}: {value}")

                if row_text_parts:
                    content = " | ".join(row_text_parts)
                    metadata = {
                        "source": file_path,
                        "file_type": "excel",
                        "row": idx + 1
                    }
                    if sheet_name:
                        metadata["sheet"] = sheet_name

                    documents.append(
                        Document(page_content=content, metadata=metadata)
                    )

        if not documents:
            return [
                Document(
                    page_content="",
                    metadata={"source": file_path, "file_type": "excel"}
                )
            ]

        return documents


class PowerPointLoader(BaseDocumentLoader):
    """
    PowerPoint 文档加载器
    支持 .ppt, .pptx
    """

    @property
    def supported_extensions(self) -> List[str]:
        return [".ppt", ".pptx", ".pptm"]

    def load(self, file_path: str) -> List[Document]:
        try:
            from pptx import Presentation
        except ImportError:
            raise ImportError(
                "PowerPoint 文档加载需要安装 python-pptx 库。请运行: pip install python-pptx"
            )

        prs = Presentation(file_path)
        documents = []

        for slide_idx, slide in enumerate(prs.slides):
            slide_text_parts = []

            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text_parts.append(shape.text)

                if hasattr(shape, "table"):
                    table = shape.table
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            if cell.text.strip():
                                row_text.append(cell.text)
                        if row_text:
                            slide_text_parts.append(" | ".join(row_text))

            if slide_text_parts:
                content = "\n".join(slide_text_parts)
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file_path,
                            "file_type": "powerpoint",
                            "slide": slide_idx + 1
                        }
                    )
                )

        if not documents:
            return [
                Document(
                    page_content="",
                    metadata={"source": file_path, "file_type": "powerpoint"}
                )
            ]

        return documents


class DocumentLoaderFactory:
    """
    文档加载器工厂
    根据文件扩展名选择合适的加载器
    """

    def __init__(self):
        self._loaders: List[BaseDocumentLoader] = []
        self._loader_cache: Dict[str, BaseDocumentLoader] = {}
        self._register_default_loaders()

    def _register_default_loaders(self):
        """注册默认的文档加载器"""
        self.register_loader(PDFLoader())
        self.register_loader(TextLoader())
        self.register_loader(WordLoader())
        self.register_loader(ExcelLoader())
        self.register_loader(PowerPointLoader())

    def register_loader(self, loader: BaseDocumentLoader):
        """
        注册文档加载器

        Args:
            loader: 文档加载器实例
        """
        self._loaders.append(loader)

        for ext in loader.supported_extensions:
            self._loader_cache[ext.lower()] = loader

    def get_loader(self, file_extension: str) -> Optional[BaseDocumentLoader]:
        """
        根据文件扩展名获取加载器

        Args:
            file_extension: 文件扩展名（带或不带点号）

        Returns:
            对应的文档加载器，如果不支持则返回 None
        """
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = "." + ext

        return self._loader_cache.get(ext)

    def load_document(self, file_path: str) -> List[Document]:
        """
        加载文档（自动选择合适的加载器）

        Args:
            file_path: 文件路径

        Returns:
            文档列表

        Raises:
            ValueError: 如果不支持的文件类型
            ImportError: 如果缺少必要的依赖
        """
        file_extension = Path(file_path).suffix.lower()

        loader = self.get_loader(file_extension)

        if loader is None:
            raise ValueError(f"不支持的文件类型: {file_extension}")

        return loader.load(file_path)

    def get_supported_extensions(self) -> List[str]:
        """
        获取所有支持的文件扩展名

        Returns:
            支持的扩展名列表
        """
        return list(self._loader_cache.keys())

    def get_supported_types_description(self) -> str:
        """
        获取支持的文件类型描述

        Returns:
            格式化的支持类型描述字符串
        """
        type_groups = {
            "PDF": [".pdf"],
            "Word": [".doc", ".docx"],
            "Excel": [".xls", ".xlsx", ".xlsm", ".csv"],
            "PowerPoint": [".ppt", ".pptx"],
            "文本": [".txt", ".md", ".markdown", ".rst", ".log"]
        }

        descriptions = []
        for type_name, extensions in type_groups.items():
            supported_exts = [ext for ext in extensions if ext in self._loader_cache]
            if supported_exts:
                descriptions.append(f"{type_name} ({', '.join(supported_exts)})")

        return "; ".join(descriptions)


loader_factory = DocumentLoaderFactory()
