# 内部知识库系统

基于FastAPI和LangChain的RAG（检索增强生成）内部知识库系统，适合初学者快速上手RAG技术的实际应用。

## 功能特点

- 📁 **文档管理**：支持上传PDF、TXT、Markdown等多种格式的文档
- 🤖 **智能问答**：基于RAG技术的自然语言问答系统
- 🔍 **向量检索**：使用ChromaDB进行高效的相似度搜索
- ⚙️ **灵活配置**：支持配置知识库路径、向量数据库参数等
- 🎨 **友好界面**：现代化的Web界面，支持拖拽上传
- 📊 **参考资料**：显示回答的参考文档来源

## 技术栈

- **后端框架**：FastAPI 0.109.0
- **AI框架**：LangChain 0.1.0
- **向量数据库**：ChromaDB 0.4.22
- **嵌入模型**：HuggingFace Embeddings（默认all-MiniLM-L6-v2）
- **前端**：原生HTML/CSS/JavaScript
- **模板引擎**：Jinja2

## 项目结构

```
rag_knowlage/
├── config.py              # 配置管理模块
├── document_processor.py  # 文档处理和向量化模块
├── rag_system.py          # RAG问答系统模块
├── main.py                # FastAPI主应用
├── requirements.txt       # 项目依赖
├── sample_document.txt    # 示例文档
├── static/
│   ├── css/
│   │   └── style.css      # 样式文件
│   └── js/
│       └── app.js         # 前端交互脚本
└── templates/
    └── index.html         # 主页模板
```

## 快速开始

### 1. 环境准备

确保您的系统已安装Python 3.8或更高版本。

### 2. 安装依赖

```bash
# 进入项目目录
cd /Users/iphone/git/Trae/rag_knowlage

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 运行系统

```bash
# 启动FastAPI服务器
python main.py
```

服务器将在 `http://localhost:8000` 启动。

### 4. 访问系统

- **Web界面**：打开浏览器访问 `http://localhost:8000`
- **API文档**：访问 `http://localhost:8000/docs` 查看自动生成的API文档
- **ReDoc文档**：访问 `http://localhost:8000/redoc` 查看替代格式的API文档

## 使用指南

### 1. 上传文档

1. 打开Web界面，在左侧面板选择"文件管理"标签
2. 点击"选择文件"按钮或直接拖拽文件到上传区域
3. 支持的文件格式：PDF、TXT、MD、DOCX
4. 文件会自动保存到知识库目录并进行向量化处理

### 2. 智能问答

1. 在右侧聊天界面的输入框中输入问题
2. 点击"发送"按钮或按Enter键
3. 系统会：
   - 检索知识库中相关的文档片段
   - 基于检索到的内容生成回答
   - 显示参考资料来源

### 3. 系统配置

1. 切换到"系统配置"标签页
2. 可以调整以下参数：
   - **知识库存储路径**：原始文档文件的存储位置
   - **向量数据库路径**：向量化数据的存储位置
   - **文档分块大小**：文档分割时的字符数（默认1000）
   - **分块重叠大小**：相邻块的重叠字符数（默认200）
   - **检索返回文档数**：每次查询返回的相关文档数量（默认3）
3. 点击"保存配置"按钮应用更改

### 4. 数据库管理

在"文件管理"标签页底部提供了数据库操作按钮：
- **重建数据库**：清空当前向量数据库并重新处理所有文件
- **清空数据库**：仅清空向量数据库中的数据

## API接口

### 核心API

#### 文件上传
```
POST /api/upload          # 单文件上传
POST /api/upload/multiple # 多文件上传
```

#### 文件管理
```
GET    /api/files              # 获取文件列表
DELETE /api/files/{file_name}  # 删除文件
```

#### 问答系统
```
POST /api/chat    # RAG问答
POST /api/search  # 仅搜索文档（不生成回答）
```

#### 配置管理
```
GET  /api/config  # 获取配置
PUT  /api/config  # 更新配置
```

#### 数据库操作
```
POST /api/rebuild   # 重建数据库
DELETE /api/database # 清空数据库
```

#### 健康检查
```
GET /api/health  # 系统健康状态
```

## 配置说明

### 默认配置

系统默认配置在 `config.py` 中定义：

```python
# 知识库存储路径
KNOWLEDGE_BASE_PATH = "./knowledge_base"

# 向量数据库配置
VECTOR_DB_PATH = "./vector_db"
VECTOR_DB_COLLECTION_NAME = "knowledge_base"

# 文档处理配置
CHUNK_SIZE = 1000      # 分块大小
CHUNK_OVERLAP = 200    # 重叠大小

# RAG配置
RETRIEVER_TOP_K = 3    # 检索返回数量

# 嵌入模型配置
EMBEDDING_MODEL_TYPE = "local"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# LLM配置
LLM_TYPE = "local"     # 可选: "local" 或 "openai"
LLM_MODEL_NAME = "gpt-3.5-turbo"
```

### 环境变量配置

可以通过创建 `.env` 文件来覆盖默认配置：

```env
# .env 文件示例
KNOWLEDGE_BASE_PATH=./my_knowledge_base
VECTOR_DB_PATH=./my_vector_db
CHUNK_SIZE=1500
CHUNK_OVERLAP=300
RETRIEVER_TOP_K=5

# OpenAI配置（如果使用OpenAI）
LLM_TYPE=openai
OPENAI_API_KEY=your-api-key-here
```

## 使用示例文档

项目包含一个示例文档 `sample_document.txt`，您可以：

1. 直接上传该文件到系统进行测试
2. 使用该文件了解系统的文档格式要求
3. 基于该文档测试问答功能

示例测试问题：
- "这个系统支持哪些文件格式？"
- "如何配置知识库存储路径？"
- "RAG技术的核心功能是什么？"
- "文档分块大小的建议值是多少？"

## 高级配置

### 使用OpenAI LLM

1. 在 `.env` 文件中配置：
```env
LLM_TYPE=openai
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL_NAME=gpt-3.5-turbo
```

2. 安装额外依赖：
```bash
pip install langchain-openai
```

### 使用本地LLM（如Ollama）

1. 安装并启动Ollama
2. 拉取模型：`ollama pull llama2`
3. 修改 `rag_system.py` 中的 `_init_llm` 方法以支持Ollama

## 注意事项

1. **首次运行**：系统会自动创建必要的目录结构
2. **嵌入模型下载**：首次使用HuggingFace嵌入模型时，会自动下载模型文件（约100MB）
3. **大文件处理**：大型PDF文件可能需要较长时间处理，建议分批上传
4. **存储空间**：确保有足够的磁盘空间存储文档和向量数据库

## 常见问题

### Q: 上传文件失败？
A: 检查以下几点：
- 文件格式是否支持（PDF、TXT、MD、DOCX）
- 文件大小是否过大
- 磁盘空间是否充足
- 权限是否正确

### Q: 查询结果不准确？
A: 可以尝试：
- 确保已上传相关文档
- 使用更具体的问题描述
- 调整 `RETRIEVER_TOP_K` 参数增加返回文档数量
- 检查文档是否已正确处理

### Q: 如何提升系统性能？
A: 建议：
- 使用SSD存储向量数据库
- 分批处理大型文档
- 考虑使用GPU加速（如果可用）
- 定期清理不需要的文档

## 扩展开发

### 添加新的文件格式支持

1. 在 `config.py` 中更新 `SUPPORTED_FILE_TYPES`
2. 在 `document_processor.py` 的 `load_document` 方法中添加新的loader

### 自定义嵌入模型

修改 `document_processor.py` 中的 `_init_embeddings` 方法，添加新的嵌入模型支持。

### 自定义LLM

修改 `rag_system.py` 中的 `_init_llm` 方法，添加新的LLM支持。

## 许可证

本项目仅供学习和内部使用。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件到项目维护者

---

**祝您使用愉快！** 🚀
