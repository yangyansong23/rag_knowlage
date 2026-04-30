import disable_telemetry  # 必须是第一个导入，用于禁用 ChromaDB 遥测
import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager

from config import settings, ensure_directories
from document_processor import document_processor
from rag_system import rag_system
from llm_service import llm_service


class QueryRequest(BaseModel):
    question: str
    k: Optional[int] = None


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class LLMConfigRequest(BaseModel):
    llm_provider: str
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None
    openai_temperature: Optional[float] = None
    openai_max_tokens: Optional[int] = None
    generic_api_url: Optional[str] = None
    generic_api_key: Optional[str] = None
    generic_api_model: Optional[str] = None


class VectorDBConfigRequest(BaseModel):
    vector_db_type: str
    vector_db_path: Optional[str] = None
    vector_db_collection_name: Optional[str] = None

    vector_db_index_type: Optional[str] = None
    vector_db_distance_metric: Optional[str] = None
    vector_db_persist: Optional[bool] = None

    hnsw_m: Optional[int] = None
    hnsw_ef_construction: Optional[int] = None
    hnsw_ef_search: Optional[int] = None
    ivf_nlist: Optional[int] = None
    ivf_nprobe: Optional[int] = None

    qdrant_host: Optional[str] = None
    qdrant_port: Optional[int] = None
    qdrant_api_key: Optional[str] = None

    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None

    milvus_host: Optional[str] = None
    milvus_port: Optional[int] = None
    milvus_username: Optional[str] = None
    milvus_password: Optional[str] = None
    milvus_database: Optional[str] = None
    milvus_collection: Optional[str] = None

    weaviate_host: Optional[str] = None
    weaviate_port: Optional[int] = None
    weaviate_api_key: Optional[str] = None

    pgvector_host: Optional[str] = None
    pgvector_port: Optional[int] = None
    pgvector_database: Optional[str] = None
    pgvector_username: Optional[str] = None
    pgvector_password: Optional[str] = None
    pgvector_table: Optional[str] = None


class SystemConfigRequest(BaseModel):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    retriever_top_k: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的处理"""
    print("=" * 60)
    print("正在启动内部知识库系统...")
    print("=" * 60)

    ensure_directories()

    print(f"✓ 知识库路径: {settings.KNOWLEDGE_BASE_PATH}")
    print(f"✓ 向量数据库类型: {settings.VECTOR_DB_TYPE}")
    print(f"✓ 向量数据库路径: {settings.VECTOR_DB_PATH}")
    print(f"✓ 分块大小: {settings.CHUNK_SIZE}")
    print(f"✓ 重叠大小: {settings.CHUNK_OVERLAP}")
    print(f"✓ 检索数量: {settings.RETRIEVER_TOP_K}")
    print(f"✓ LLM 提供者: {settings.LLM_PROVIDER}")

    print("=" * 60)
    print("系统启动完成！")
    print(f"请访问: http://localhost:8000")
    print("=" * 60)

    yield

    print("\n正在关闭内部知识库系统...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

static_dir = Path("static")
templates_dir = Path("templates")
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/config", response_model=APIResponse)
async def get_config():
    """获取当前配置"""
    config_data = {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "server_host": settings.SERVER_HOST,
        "server_port": settings.SERVER_PORT,
        "port_auto_find": settings.PORT_AUTO_FIND,
        "port_retry_max": settings.PORT_RETRY_MAX,
        "knowledge_base_path": settings.KNOWLEDGE_BASE_PATH,
        "vector_db_path": settings.VECTOR_DB_PATH,
        "vector_db_type": settings.VECTOR_DB_TYPE,
        "vector_db_collection_name": settings.VECTOR_DB_COLLECTION_NAME,
        "vector_db_index_type": settings.VECTOR_DB_INDEX_TYPE,
        "vector_db_distance_metric": settings.VECTOR_DB_DISTANCE_METRIC,
        "vector_db_persist": settings.VECTOR_DB_PERSIST,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "retriever_top_k": settings.RETRIEVER_TOP_K,
        "supported_file_types": settings.SUPPORTED_FILE_TYPES,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER
    }
    return APIResponse(
        success=True,
        message="配置获取成功",
        data=config_data
    )


@app.post("/api/config/llm", response_model=APIResponse)
async def save_llm_config(config: LLMConfigRequest):
    """保存 LLM 配置"""
    try:
        settings.LLM_PROVIDER = config.llm_provider
        
        if config.llm_provider == "ollama":
            if config.ollama_base_url:
                settings.OLLAMA_BASE_URL = config.ollama_base_url
            if config.ollama_model:
                settings.OLLAMA_MODEL = config.ollama_model
                
        elif config.llm_provider == "openai":
            if config.openai_api_key:
                settings.OPENAI_API_KEY = config.openai_api_key
            if config.openai_base_url:
                settings.OPENAI_BASE_URL = config.openai_base_url
            if config.openai_model:
                settings.OPENAI_MODEL = config.openai_model
            if config.openai_temperature is not None:
                settings.OPENAI_TEMPERATURE = config.openai_temperature
            if config.openai_max_tokens is not None:
                settings.OPENAI_MAX_TOKENS = config.openai_max_tokens
                
        elif config.llm_provider == "generic":
            if config.generic_api_url:
                settings.GENERIC_API_URL = config.generic_api_url
            if config.generic_api_key:
                settings.GENERIC_API_KEY = config.generic_api_key
            if config.generic_api_model:
                settings.GENERIC_API_MODEL = config.generic_api_model
        
        llm_service._initialized = False
        llm_service.initialize()
        
        return APIResponse(
            success=True,
            message=f"LLM 配置已保存，当前提供者: {config.llm_provider}",
            data={
                "llm_provider": config.llm_provider,
                "llm_status": llm_service.get_status()
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"保存配置失败: {str(e)}",
            data=None
        )


@app.post("/api/config/llm/test", response_model=APIResponse)
async def test_llm_config(request: dict):
    """测试 LLM 配置"""
    try:
        test_message = request.get("test_message", "Hello, this is a test.")
        
        response = llm_service.generate(test_message)
        
        if response and "错误" not in response and "抱歉" not in response[:50]:
            return APIResponse(
                success=True,
                message="LLM 连接测试成功",
                data={
                    "test_response": response[:200] if len(response) > 200 else response
                }
            )
        else:
            return APIResponse(
                success=False,
                message=f"LLM 测试响应异常: {response}",
                data=None
            )
            
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"LLM 测试失败: {str(e)}",
            data=None
        )


@app.post("/api/config/vector-db", response_model=APIResponse)
async def save_vector_db_config(config: VectorDBConfigRequest):
    """保存向量数据库配置"""
    try:
        settings.VECTOR_DB_TYPE = config.vector_db_type

        if config.vector_db_path:
            settings.VECTOR_DB_PATH = config.vector_db_path
        if config.vector_db_collection_name:
            settings.VECTOR_DB_COLLECTION_NAME = config.vector_db_collection_name

        if config.vector_db_index_type:
            settings.VECTOR_DB_INDEX_TYPE = config.vector_db_index_type
        if config.vector_db_distance_metric:
            settings.VECTOR_DB_DISTANCE_METRIC = config.vector_db_distance_metric
        if config.vector_db_persist is not None:
            settings.VECTOR_DB_PERSIST = config.vector_db_persist

        if config.vector_db_type == "qdrant":
            if config.qdrant_host:
                settings.QDRANT_HOST = config.qdrant_host
            if config.qdrant_port is not None:
                settings.QDRANT_PORT = config.qdrant_port
            if config.qdrant_api_key:
                settings.QDRANT_API_KEY = config.qdrant_api_key

        elif config.vector_db_type == "pinecone":
            if config.pinecone_api_key:
                settings.PINECONE_API_KEY = config.pinecone_api_key
            if config.pinecone_environment:
                settings.PINECONE_ENVIRONMENT = config.pinecone_environment
            if config.pinecone_index_name:
                settings.PINECONE_INDEX_NAME = config.pinecone_index_name

        return APIResponse(
            success=True,
            message=f"向量数据库配置已保存，当前类型: {config.vector_db_type}。请重建数据库以应用新配置。",
            data={
                "vector_db_type": config.vector_db_type,
                "index_type": config.vector_db_index_type,
                "distance_metric": config.vector_db_distance_metric
            }
        )

    except Exception as e:
        return APIResponse(
            success=False,
            message=f"保存配置失败: {str(e)}",
            data=None
        )


@app.post("/api/config/system", response_model=APIResponse)
async def save_system_config(config: SystemConfigRequest):
    """保存系统配置"""
    try:
        if config.chunk_size is not None:
            settings.CHUNK_SIZE = config.chunk_size
        if config.chunk_overlap is not None:
            settings.CHUNK_OVERLAP = config.chunk_overlap
        if config.retriever_top_k is not None:
            settings.RETRIEVER_TOP_K = config.retriever_top_k
        
        return APIResponse(
            success=True,
            message="系统配置已保存",
            data={
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
                "retriever_top_k": settings.RETRIEVER_TOP_K
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"保存配置失败: {str(e)}",
            data=None
        )


@app.post("/api/upload", response_model=APIResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件到知识库"""
    try:
        file_extension = Path(file.filename).suffix.lower().lstrip(".")
        if file_extension not in settings.SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的类型: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
            )

        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        file_path = kb_path / file.filename

        counter = 1
        while file_path.exists():
            name_stem = Path(file.filename).stem
            name_suffix = Path(file.filename).suffix
            file_path = kb_path / f"{name_stem}_{counter}{name_suffix}"
            counter += 1

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            chunk_count = document_processor.add_file(str(file_path))

            return APIResponse(
                success=True,
                message=f"文件 '{file.filename}' 上传并处理成功",
                data={
                    "file_name": file.filename,
                    "file_path": str(file_path),
                    "chunk_count": chunk_count
                }
            )
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"文件处理失败: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.post("/api/upload/multiple", response_model=APIResponse)
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """批量上传文件到知识库"""
    results = []
    errors = []

    for file in files:
        try:
            file_extension = Path(file.filename).suffix.lower().lstrip(".")
            if file_extension not in settings.SUPPORTED_FILE_TYPES:
                errors.append(f"{file.filename}: 不支持的文件类型")
                continue

            kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
            file_path = kb_path / file.filename

            counter = 1
            while file_path.exists():
                name_stem = Path(file.filename).stem
                name_suffix = Path(file.filename).suffix
                file_path = kb_path / f"{name_stem}_{counter}{name_suffix}"
                counter += 1

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            chunk_count = document_processor.add_file(str(file_path))

            results.append({
                "file_name": file.filename,
                "file_path": str(file_path),
                "chunk_count": chunk_count
            })

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")

    if errors:
        return APIResponse(
            success=False,
            message=f"部分文件上传失败。成功: {len(results)}, 失败: {len(errors)}",
            data={
                "success_files": results,
                "errors": errors
            }
        )

    return APIResponse(
        success=True,
        message=f"成功上传 {len(results)} 个文件",
        data={"files": results}
    )


@app.get("/api/files", response_model=APIResponse)
async def list_files():
    """列出知识库中的所有文件"""
    try:
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)

        if not kb_path.exists():
            return APIResponse(
                success=True,
                message="知识库目录不存在",
                data={"files": [], "total_count": 0}
            )

        files = []
        for file_path in kb_path.iterdir():
            if file_path.is_file():
                file_stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_stat.st_size,
                    "modified_time": file_stat.st_mtime
                })

        return APIResponse(
            success=True,
            message=f"共找到 {len(files)} 个文件",
            data={
                "files": files,
                "total_count": len(files),
                "knowledge_base_path": str(kb_path)
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.delete("/api/files/{file_name}", response_model=APIResponse)
async def delete_file(file_name: str):
    """从知识库中删除文件"""
    try:
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        file_path = kb_path / file_name

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"文件 '{file_name}' 不存在"
            )

        file_path.unlink()

        return APIResponse(
            success=True,
            message=f"文件 '{file_name}' 已删除。注意：向量数据库中的数据需要重新生成。",
            data={"file_name": file_name}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@app.post("/api/chat", response_model=APIResponse)
async def chat(query_request: QueryRequest):
    """RAG 问答接口"""
    try:
        question = query_request.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="问题不能为空"
            )

        print(f"\n收到用户问题: {question}")

        result = rag_system.query(question)

        print(f"返回回答，包含 {len(result.get('sources', []))} 个参考资料")

        return APIResponse(
            success=True,
            message="查询成功",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"查询错误: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@app.post("/api/search", response_model=APIResponse)
async def search_documents(query_request: QueryRequest):
    """仅搜索相关文档，不生成回答"""
    try:
        query = query_request.question.strip()
        k = query_request.k

        if not query:
            raise HTTPException(
                status_code=400,
                detail="查询不能为空"
            )

        results = rag_system.search_documents(query, k)

        return APIResponse(
            success=True,
            message=f"找到 {len(results)} 个相关文档",
            data={"documents": results}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.delete("/api/database", response_model=APIResponse)
async def clear_database():
    """清空向量数据库"""
    try:
        document_processor.clear_database()

        return APIResponse(
            success=True,
            message="向量数据库已清空",
            data=None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空数据库失败: {str(e)}")


@app.post("/api/rebuild", response_model=APIResponse)
async def rebuild_database():
    """重新构建向量数据库"""
    try:
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)

        if not kb_path.exists():
            raise HTTPException(
                status_code=404,
                detail="知识库目录不存在"
            )

        result = document_processor.rebuild_from_directory(str(kb_path))

        if result["success"]:
            return APIResponse(
                success=True,
                message=f"数据库重建完成，共处理 {result['total_files']} 个文件，生成 {result['total_chunks']} 个文档块",
                data=result
            )
        else:
            return APIResponse(
                success=False,
                message=result.get("message", "重建失败"),
                data=result
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建数据库失败: {str(e)}")


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    try:
        db_status = rag_system.get_database_status()
        llm_status = rag_system.get_llm_status()

        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        kb_exists = kb_path.exists()
        kb_file_count = 0
        if kb_exists:
            kb_file_count = len([f for f in kb_path.iterdir() if f.is_file()])

        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": db_status,
            "llm": llm_status,
            "vector_db": {
                "type": settings.VECTOR_DB_TYPE
            },
            "knowledge_base": {
                "exists": kb_exists,
                "file_count": kb_file_count,
                "path": str(kb_path)
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


def run_server():
    """运行服务器，处理端口自动选择"""
    import uvicorn
    from port_manager import port_manager

    print(f"\n{'=' * 60}")
    print(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"{'=' * 60}")

    final_port = port_manager.get_server_port()
    final_host = settings.SERVER_HOST

    print(f"\n服务器配置:")
    print(f"  - 主机地址: {final_host}")
    print(f"  - 服务端口: {final_port}")
    print(f"  - 自动端口查找: {'启用' if settings.PORT_AUTO_FIND else '禁用'}")
    print(f"  - 最大重试次数: {settings.PORT_RETRY_MAX}")
    print(f"\n{'=' * 60}")
    print(f"服务已就绪，请访问: http://localhost:{final_port}")
    print(f"{'=' * 60}\n")

    uvicorn.run(
        "main:app",
        host=final_host,
        port=final_port,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    run_server()
