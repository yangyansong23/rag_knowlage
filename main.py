import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager

from config import settings, ensure_directories
from document_processor import document_processor
from rag_system import rag_system


# 定义请求模型
class QueryRequest(BaseModel):
    question: str
    k: Optional[int] = None


class ConfigUpdateRequest(BaseModel):
    knowledge_base_path: Optional[str] = None
    vector_db_path: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    retriever_top_k: Optional[int] = None


# 定义响应模型
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的处理"""
    # 启动时执行
    print("正在启动内部知识库系统...")
    ensure_directories()
    print(f"知识库路径: {settings.KNOWLEDGE_BASE_PATH}")
    print(f"向量数据库路径: {settings.VECTOR_DB_PATH}")
    print("系统启动完成！")
    yield
    # 关闭时执行
    print("正在关闭内部知识库系统...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# 确保静态文件和模板目录存在
static_dir = Path("static")
templates_dir = Path("templates")
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")


# 路由定义
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
        "knowledge_base_path": settings.KNOWLEDGE_BASE_PATH,
        "vector_db_path": settings.VECTOR_DB_PATH,
        "vector_db_collection_name": settings.VECTOR_DB_COLLECTION_NAME,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "embedding_model_type": settings.EMBEDDING_MODEL_TYPE,
        "embedding_model_name": settings.EMBEDDING_MODEL_NAME,
        "llm_type": settings.LLM_TYPE,
        "llm_model_name": settings.LLM_MODEL_NAME,
        "retriever_top_k": settings.RETRIEVER_TOP_K,
        "supported_file_types": settings.SUPPORTED_FILE_TYPES
    }
    return APIResponse(
        success=True,
        message="配置获取成功",
        data=config_data
    )


@app.put("/api/config", response_model=APIResponse)
async def update_config(config_update: ConfigUpdateRequest):
    """更新配置"""
    try:
        # 更新配置（注意：这里只是临时更新，重启后会恢复默认值）
        # 实际生产环境应该使用持久化存储
        if config_update.knowledge_base_path:
            settings.KNOWLEDGE_BASE_PATH = config_update.knowledge_base_path
            # 确保目录存在
            Path(settings.KNOWLEDGE_BASE_PATH).mkdir(parents=True, exist_ok=True)
        
        if config_update.vector_db_path:
            settings.VECTOR_DB_PATH = config_update.vector_db_path
            # 确保目录存在
            Path(settings.VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
        
        if config_update.chunk_size:
            settings.CHUNK_SIZE = config_update.chunk_size
        
        if config_update.chunk_overlap:
            settings.CHUNK_OVERLAP = config_update.chunk_overlap
        
        if config_update.retriever_top_k:
            settings.RETRIEVER_TOP_K = config_update.retriever_top_k
            # 刷新RAG链
            rag_system.refresh_chain()
        
        return APIResponse(
            success=True,
            message="配置更新成功",
            data={
                "knowledge_base_path": settings.KNOWLEDGE_BASE_PATH,
                "vector_db_path": settings.VECTOR_DB_PATH,
                "chunk_size": settings.CHUNK_SIZE,
                "chunk_overlap": settings.CHUNK_OVERLAP,
                "retriever_top_k": settings.RETRIEVER_TOP_K
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@app.post("/api/upload", response_model=APIResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传文件到知识库"""
    try:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower().lstrip(".")
        if file_extension not in settings.SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的类型: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
            )
        
        # 保存文件到知识库目录
        kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        file_path = kb_path / file.filename
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        while file_path.exists():
            name_stem = Path(file.filename).stem
            name_suffix = Path(file.filename).suffix
            file_path = kb_path / f"{name_stem}_{counter}{name_suffix}"
            counter += 1
        
        # 写入文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 将文件添加到向量数据库
        try:
            ids = document_processor.add_file(str(file_path))
            # 刷新RAG链
            rag_system.refresh_chain()
            
            return APIResponse(
                success=True,
                message=f"文件 '{file.filename}' 上传并处理成功",
                data={
                    "file_name": file.filename,
                    "file_path": str(file_path),
                    "document_count": len(ids)
                }
            )
        except Exception as e:
            # 如果处理失败，删除已保存的文件
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
            # 检查文件类型
            file_extension = Path(file.filename).suffix.lower().lstrip(".")
            if file_extension not in settings.SUPPORTED_FILE_TYPES:
                errors.append(f"{file.filename}: 不支持的文件类型")
                continue
            
            # 保存文件到知识库目录
            kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
            file_path = kb_path / file.filename
            
            # 如果文件已存在，添加数字后缀
            counter = 1
            while file_path.exists():
                name_stem = Path(file.filename).stem
                name_suffix = Path(file.filename).suffix
                file_path = kb_path / f"{name_stem}_{counter}{name_suffix}"
                counter += 1
            
            # 写入文件
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 将文件添加到向量数据库
            ids = document_processor.add_file(str(file_path))
            
            results.append({
                "file_name": file.filename,
                "file_path": str(file_path),
                "document_count": len(ids)
            })
            
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
    
    # 刷新RAG链
    rag_system.refresh_chain()
    
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
        
        # 删除文件
        file_path.unlink()
        
        # 注意：这里只是删除了原始文件，向量数据库中的数据需要单独处理
        # 简化实现中，我们提示用户需要重新处理所有文件或清空数据库
        
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
    """RAG问答接口"""
    try:
        question = query_request.question.strip()
        
        if not question:
            raise HTTPException(
                status_code=400,
                detail="问题不能为空"
            )
        
        # 执行RAG查询
        result = rag_system.query(question)
        
        return APIResponse(
            success=True,
            message="查询成功",
            data=result
        )
    
    except HTTPException:
        raise
    except Exception as e:
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
        
        # 搜索相关文档
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
        rag_system.refresh_chain()
        
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
        
        # 清空现有数据库
        document_processor.clear_database()
        
        # 处理所有文件
        total_documents = 0
        processed_files = []
        
        for file_path in kb_path.iterdir():
            if file_path.is_file():
                try:
                    ids = document_processor.add_file(str(file_path))
                    total_documents += len(ids)
                    processed_files.append({
                        "file_name": file_path.name,
                        "document_count": len(ids)
                    })
                except Exception as e:
                    processed_files.append({
                        "file_name": file_path.name,
                        "error": str(e)
                    })
        
        # 刷新RAG链
        rag_system.refresh_chain()
        
        return APIResponse(
            success=True,
            message=f"数据库重建完成，共处理 {len(processed_files)} 个文件，生成 {total_documents} 个文档块",
            data={
                "total_files": len(processed_files),
                "total_documents": total_documents,
                "files": processed_files
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建数据库失败: {str(e)}")


# 健康检查接口
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
