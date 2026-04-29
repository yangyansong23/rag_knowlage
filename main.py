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


# 定义请求模型
class QueryRequest(BaseModel):
    question: str
    k: Optional[int] = None


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
    print("=" * 60)
    print("正在启动内部知识库系统...")
    print("=" * 60)

    # 确保必要的目录存在
    ensure_directories()

    print(f"✓ 知识库路径: {settings.KNOWLEDGE_BASE_PATH}")
    print(f"✓ 向量数据库路径: {settings.VECTOR_DB_PATH}")
    print(f"✓ 分块大小: {settings.CHUNK_SIZE}")
    print(f"✓ 重叠大小: {settings.CHUNK_OVERLAP}")
    print(f"✓ 检索数量: {settings.RETRIEVER_TOP_K}")

    print("=" * 60)
    print("系统启动完成！")
    print(f"请访问: http://localhost:8000")
    print("=" * 60)

    yield

    # 关闭时执行
    print("\n正在关闭内部知识库系统...")


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
        "retriever_top_k": settings.RETRIEVER_TOP_K,
        "supported_file_types": settings.SUPPORTED_FILE_TYPES
    }
    return APIResponse(
        success=True,
        message="配置获取成功",
        data=config_data
    )


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

        # 删除文件
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
    """RAG问答接口"""
    try:
        question = query_request.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="问题不能为空"
            )

        print(f"\n收到用户问题: {question}")

        # 执行RAG查询
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

        # 从目录重建
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

        # 检查知识库目录
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