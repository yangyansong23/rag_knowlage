// 全局变量
let currentModalCallback = null;

// DOM元素
const dom = {
    // 标签页
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // 文件上传
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    selectFileBtn: document.getElementById('selectFileBtn'),
    uploadProgress: document.getElementById('uploadProgress'),
    progressFill: document.getElementById('progressFill'),
    uploadStatus: document.getElementById('uploadStatus'),
    
    // 文件列表
    fileList: document.getElementById('fileList'),
    refreshFilesBtn: document.getElementById('refreshFilesBtn'),
    
    // 数据库操作
    rebuildBtn: document.getElementById('rebuildBtn'),
    clearBtn: document.getElementById('clearBtn'),
    
    // 聊天
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    docCount: document.getElementById('docCount'),
    dbStatus: document.getElementById('dbStatus'),
    llmStatus: document.getElementById('llmStatus'),
    
    // 参考资料
    referencesPanel: document.getElementById('referencesPanel'),
    refContent: document.getElementById('refContent'),
    toggleRefBtn: document.getElementById('toggleRefBtn'),
    
    // 状态显示
    statusDisplay: document.getElementById('statusDisplay'),
    llmStatusDisplay: document.getElementById('llmStatusDisplay'),
    vectorDbStatusDisplay: document.getElementById('vectorDbStatusDisplay'),
    
    // LLM 配置
    llmProvider: document.getElementById('llmProvider'),
    saveLlmConfig: document.getElementById('saveLlmConfig'),
    testLlmConfig: document.getElementById('testLlmConfig'),
    
    // Ollama 配置
    ollamaBaseUrl: document.getElementById('ollamaBaseUrl'),
    ollamaModel: document.getElementById('ollamaModel'),
    
    // OpenAI 配置
    openaiApiKey: document.getElementById('openaiApiKey'),
    openaiBaseUrl: document.getElementById('openaiBaseUrl'),
    openaiModel: document.getElementById('openaiModel'),
    openaiTemperature: document.getElementById('openaiTemperature'),
    openaiMaxTokens: document.getElementById('openaiMaxTokens'),
    
    // 通用 API 配置
    genericApiUrl: document.getElementById('genericApiUrl'),
    genericApiKey: document.getElementById('genericApiKey'),
    genericApiModel: document.getElementById('genericApiModel'),
    
    // 向量数据库配置
    vectorDbType: document.getElementById('vectorDbType'),
    saveVectorDbConfig: document.getElementById('saveVectorDbConfig'),
    
    // 系统配置
    chunkSize: document.getElementById('chunkSize'),
    chunkOverlap: document.getElementById('chunkOverlap'),
    retrieverK: document.getElementById('retrieverK'),
    saveSystemConfig: document.getElementById('saveSystemConfig'),
    
    // 提示框
    toast: document.getElementById('toast'),
    
    // 模态框
    modal: document.getElementById('modal'),
    modalTitle: document.getElementById('modalTitle'),
    modalMessage: document.getElementById('modalMessage'),
    modalCancel: document.getElementById('modalCancel'),
    modalConfirm: document.getElementById('modalConfirm')
};

// 初始化
document.addEventListener('DOMContentLoaded', init);

function init() {
    initTabs();
    initUpload();
    initChat();
    initConfigEvents();
    initEvents();
    loadData();
}

// 标签页切换
function initTabs() {
    dom.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // 更新按钮状态
            dom.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 更新内容显示
            dom.tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

// 文件上传
function initUpload() {
    // 选择文件按钮
    dom.selectFileBtn.addEventListener('click', () => {
        dom.fileInput.click();
    });
    
    // 文件选择
    dom.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFiles(e.target.files);
        }
    });
    
    // 拖拽上传
    dom.uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        dom.uploadArea.classList.add('drag-over');
    });
    
    dom.uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dom.uploadArea.classList.remove('drag-over');
    });
    
    dom.uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dom.uploadArea.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });
}

// 聊天功能
function initChat() {
    // 发送按钮
    dom.sendBtn.addEventListener('click', sendMessage);
    
    // 键盘事件
    dom.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 自动调整高度
    dom.chatInput.addEventListener('input', () => {
        dom.chatInput.style.height = 'auto';
        dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 100) + 'px';
    });
    
    // 参考资料切换
    dom.toggleRefBtn.addEventListener('click', () => {
        const isVisible = dom.refContent.style.display !== 'none';
        dom.refContent.style.display = isVisible ? 'none' : 'block';
        dom.toggleRefBtn.textContent = isVisible ? '展开' : '收起';
    });
}

// 配置事件
function initConfigEvents() {
    // LLM 提供者切换
    if (dom.llmProvider) {
        dom.llmProvider.addEventListener('change', (e) => {
            updateLlmConfigDisplay(e.target.value);
        });
    }
    
    // 向量数据库类型切换
    if (dom.vectorDbType) {
        dom.vectorDbType.addEventListener('change', (e) => {
            updateVectorDbConfigDisplay(e.target.value);
        });
    }
    
    // 保存 LLM 配置
    if (dom.saveLlmConfig) {
        dom.saveLlmConfig.addEventListener('click', saveLlmConfiguration);
    }
    
    // 测试 LLM 配置
    if (dom.testLlmConfig) {
        dom.testLlmConfig.addEventListener('click', testLlmConfiguration);
    }
    
    // 保存向量数据库配置
    if (dom.saveVectorDbConfig) {
        dom.saveVectorDbConfig.addEventListener('click', saveVectorDbConfiguration);
    }
    
    // 保存系统配置
    if (dom.saveSystemConfig) {
        dom.saveSystemConfig.addEventListener('click', saveSystemConfiguration);
    }
}

// 更新 LLM 配置显示
function updateLlmConfigDisplay(providerType) {
    // 隐藏所有配置
    document.querySelectorAll('.provider-config').forEach(el => {
        el.style.display = 'none';
    });
    
    // 显示对应配置
    if (providerType === 'ollama') {
        document.getElementById('ollama-config').style.display = 'block';
    } else if (providerType === 'openai') {
        document.getElementById('openai-config').style.display = 'block';
    } else if (providerType === 'generic') {
        document.getElementById('generic-config').style.display = 'block';
    }
}

// 更新向量数据库配置显示
function updateVectorDbConfigDisplay(dbType) {
    // 隐藏所有配置
    document.querySelectorAll('.db-config').forEach(el => {
        el.style.display = 'none';
    });
    
    // 显示对应配置
    document.getElementById(`${dbType}-config`).style.display = 'block';
}

// 事件监听
function initEvents() {
    // 刷新文件列表
    dom.refreshFilesBtn.addEventListener('click', loadFileList);
    
    // 重建数据库
    dom.rebuildBtn.addEventListener('click', () => {
        showModal(
            '确认重建数据库',
            '这将清空当前向量数据库并重新处理所有文件。确定继续吗？',
            rebuildDatabase
        );
    });
    
    // 清空数据库
    dom.clearBtn.addEventListener('click', () => {
        showModal(
            '确认清空数据库',
            '这将清空向量数据库中的所有数据。此操作不可撤销。确定继续吗？',
            clearDatabase
        );
    });
    
    // 模态框按钮
    dom.modalCancel.addEventListener('click', hideModal);
}

// 加载初始数据
function loadData() {
    loadFileList();
    loadStatus();
    loadCurrentConfig();
}

// 加载当前配置
function loadCurrentConfig() {
    // 获取系统配置
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data) {
                const config = data.data;
                
                // 更新 LLM 配置
                if (config.llm_provider) {
                    dom.llmProvider.value = config.llm_provider;
                    updateLlmConfigDisplay(config.llm_provider);
                }
                
                // 更新向量数据库配置
                if (config.vector_db_type) {
                    dom.vectorDbType.value = config.vector_db_type;
                    updateVectorDbConfigDisplay(config.vector_db_type);
                }
                
                // 更新系统配置
                if (config.chunk_size) {
                    dom.chunkSize.value = config.chunk_size;
                }
                if (config.chunk_overlap) {
                    dom.chunkOverlap.value = config.chunk_overlap;
                }
                if (config.retriever_top_k) {
                    dom.retrieverK.value = config.retriever_top_k;
                }
            }
        })
        .catch(error => {
            console.error('加载配置失败:', error);
        });
}

// 加载文件列表
async function loadFileList() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (data.success) {
            const files = data.data.files || [];
            
            // 更新文档数量显示
            dom.docCount.textContent = `${data.data.total_count || 0} 个文件`;
            
            // 更新文件列表
            if (files.length === 0) {
                dom.fileList.innerHTML = '<p class="empty">暂无文件，请上传文档</p>';
            } else {
                dom.fileList.innerHTML = files.map(file => `
                    <div class="file-item">
                        <div class="file-info">
                            <div class="file-name">${file.name}</div>
                            <div class="file-meta">${formatFileSize(file.size)} | ${formatDate(file.modified_time)}</div>
                        </div>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
        dom.fileList.innerHTML = '<p class="empty">加载失败，请刷新重试</p>';
    }
}

// 加载系统状态
async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.status === 'healthy') {
            // 系统状态
            dom.statusDisplay.innerHTML = `
                <p><strong>应用状态:</strong> 正常运行</p>
                <p><strong>知识库路径:</strong> ${data.knowledge_base.path}</p>
                <p><strong>知识库文件数:</strong> ${data.knowledge_base.file_count}</p>
                <p><strong>向量数据库文档数:</strong> ${data.database.document_count}</p>
                <p><strong>集合名称:</strong> ${data.database.collection_name}</p>
                <p><strong>向量数据库类型:</strong> ${data.database.vector_db_type || 'chroma'}</p>
            `;
            
            dom.dbStatus.textContent = `就绪 (${data.database.document_count} 个文档块)`;
            
            // LLM 状态
            if (data.llm) {
                const llmProvider = data.llm.active_provider || 'rule_based';
                const providerNames = {
                    'ollama': '本地 LLM (Ollama)',
                    'openai': 'OpenAI API',
                    'generic': '通用 API',
                    'rule_based': '规则模式'
                };
                
                dom.llmStatusDisplay.innerHTML = `
                    <p><strong>当前提供者:</strong> ${providerNames[llmProvider] || llmProvider}</p>
                    <p><strong>初始化状态:</strong> ${data.llm.initialized ? '已初始化' : '未初始化'}</p>
                `;
                
                dom.llmStatus.textContent = providerNames[llmProvider] || llmProvider;
            }
            
            // 向量数据库状态
            if (data.vector_db) {
                dom.vectorDbStatusDisplay.innerHTML = `
                    <p><strong>数据库类型:</strong> ${data.vector_db.type || 'chroma'}</p>
                    <p><strong>文档数:</strong> ${data.database.document_count}</p>
                `;
            }
        }
    } catch (error) {
        console.error('加载状态失败:', error);
        dom.statusDisplay.innerHTML = '<p>状态加载失败</p>';
    }
}

// 上传文件
async function uploadFiles(files) {
    if (files.length === 0) return;
    
    // 显示进度
    dom.uploadProgress.style.display = 'block';
    dom.progressFill.style.width = '0%';
    dom.uploadStatus.textContent = '正在上传...';
    
    // 禁用上传区域
    dom.uploadArea.style.pointerEvents = 'none';
    
    const formData = new FormData();
    
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        // 更新进度
        dom.progressFill.style.width = '30%';
        dom.uploadStatus.textContent = '正在处理文件...';
        
        const response = await fetch('/api/upload/multiple', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // 更新进度
        dom.progressFill.style.width = '100%';
        
        if (response.ok && data.success) {
            dom.uploadStatus.textContent = '上传成功！';
            showToast(data.message, 'success');
            loadFileList();
            loadStatus();
        } else {
            dom.uploadStatus.textContent = '上传失败';
            showToast(data.message || '上传失败', 'error');
        }
    } catch (error) {
        dom.uploadStatus.textContent = '上传失败';
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        // 重置
        setTimeout(() => {
            dom.uploadProgress.style.display = 'none';
            dom.uploadArea.style.pointerEvents = 'auto';
            dom.fileInput.value = '';
        }, 1500);
    }
}

// 发送消息
async function sendMessage() {
    const question = dom.chatInput.value.trim();
    
    if (!question) {
        showToast('请输入问题', 'info');
        return;
    }
    
    // 添加用户消息
    addMessage(question, 'user');
    
    // 清空输入
    dom.chatInput.value = '';
    dom.chatInput.style.height = 'auto';
    
    // 显示加载动画
    const loadingId = addLoading();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: question })
        });
        
        const data = await response.json();
        
        // 移除加载动画
        removeLoading(loadingId);
        
        if (data.success) {
            // 添加助手回答
            addMessage(data.data.answer, 'assistant');
            
            // 显示参考资料
            if (data.data.sources && data.data.sources.length > 0) {
                showReferences(data.data.sources);
            }
        } else {
            addMessage('抱歉，处理您的问题时出现错误。', 'assistant');
        }
    } catch (error) {
        removeLoading(loadingId);
        addMessage('抱歉，发生了错误: ' + error.message, 'assistant');
        showToast('查询失败: ' + error.message, 'error');
    }
}

// 添加消息
function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 处理换行
    const formattedContent = content
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    contentDiv.innerHTML = `<p>${formattedContent}</p>`;
    messageDiv.appendChild(contentDiv);
    
    dom.chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 添加加载动画
function addLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.id = `loading-${Date.now()}`;
    
    loadingDiv.innerHTML = `
        <div class="loading">
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    
    dom.chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    
    return loadingDiv.id;
}

// 移除加载动画
function removeLoading(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// 显示参考资料
function showReferences(sources) {
    dom.referencesPanel.style.display = 'flex';
    dom.refContent.style.display = 'block';
    dom.toggleRefBtn.textContent = '收起';
    
    dom.refContent.innerHTML = sources.map((source, index) => `
        <div class="ref-item">
            <div class="ref-source">
                参考 ${index + 1}: ${source.metadata.source || '未知来源'}
            </div>
            <div class="ref-text">
                ${source.content.substring(0, 400)}${source.content.length > 400 ? '...' : ''}
            </div>
        </div>
    `).join('');
}

// 滚动到底部
function scrollToBottom() {
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// 保存 LLM 配置
async function saveLlmConfiguration() {
    const providerType = dom.llmProvider.value;
    const config = {
        llm_provider: providerType
    };
    
    if (providerType === 'ollama') {
        config.ollama_base_url = dom.ollamaBaseUrl.value;
        config.ollama_model = dom.ollamaModel.value;
    } else if (providerType === 'openai') {
        config.openai_api_key = dom.openaiApiKey.value;
        config.openai_base_url = dom.openaiBaseUrl.value;
        config.openai_model = dom.openaiModel.value;
        config.openai_temperature = parseFloat(dom.openaiTemperature.value);
        config.openai_max_tokens = parseInt(dom.openaiMaxTokens.value);
    } else if (providerType === 'generic') {
        config.generic_api_url = dom.genericApiUrl.value;
        config.generic_api_key = dom.genericApiKey.value;
        config.generic_api_model = dom.genericApiModel.value;
    }
    
    try {
        const response = await fetch('/api/config/llm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('LLM 配置已保存', 'success');
            loadStatus();
        } else {
            showToast(data.message || '保存失败', 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// 测试 LLM 配置
async function testLlmConfiguration() {
    showToast('正在测试 LLM 连接...', 'info');
    
    try {
        const response = await fetch('/api/config/llm/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ test_message: 'Hello' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('LLM 连接测试成功！', 'success');
        } else {
            showToast('测试失败: ' + data.message, 'error');
        }
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    }
}

// 保存向量数据库配置
async function saveVectorDbConfiguration() {
    const dbType = dom.vectorDbType.value;
    const config = {
        vector_db_type: dbType
    };
    
    // 根据数据库类型添加特定配置
    if (dbType === 'chroma') {
        config.vector_db_path = dom.chromaPath?.value;
        config.vector_db_collection_name = dom.chromaCollection?.value;
    } else if (dbType === 'faiss') {
        config.vector_db_path = dom.faissPath?.value;
    } else if (dbType === 'qdrant') {
        config.qdrant_host = dom.qdrantHost?.value;
        config.qdrant_port = parseInt(dom.qdrantPort?.value) || 6333;
        config.qdrant_api_key = dom.qdrantApiKey?.value;
        config.vector_db_collection_name = dom.qdrantCollection?.value;
    } else if (dbType === 'pinecone') {
        config.pinecone_api_key = dom.pineconeApiKey?.value;
        config.pinecone_environment = dom.pineconeEnvironment?.value;
        config.pinecone_index_name = dom.pineconeIndexName?.value;
    }
    
    try {
        const response = await fetch('/api/config/vector-db', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('向量数据库配置已保存。请重建数据库以应用新配置。', 'success');
            loadStatus();
        } else {
            showToast(data.message || '保存失败', 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// 保存系统配置
async function saveSystemConfiguration() {
    const config = {
        chunk_size: parseInt(dom.chunkSize.value),
        chunk_overlap: parseInt(dom.chunkOverlap.value),
        retriever_top_k: parseInt(dom.retrieverK.value)
    };
    
    try {
        const response = await fetch('/api/config/system', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('系统配置已保存', 'success');
            loadStatus();
        } else {
            showToast(data.message || '保存失败', 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// 重建数据库
async function rebuildDatabase() {
    hideModal();
    showToast('正在重建数据库，请稍候...', 'info');
    
    try {
        const response = await fetch('/api/rebuild', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            loadFileList();
            loadStatus();
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('重建失败: ' + error.message, 'error');
    }
}

// 清空数据库
async function clearDatabase() {
    hideModal();
    
    try {
        const response = await fetch('/api/database', {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('数据库已清空', 'success');
            loadStatus();
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        showToast('清空失败: ' + error.message, 'error');
    }
}

// 显示模态框
function showModal(title, message, callback) {
    dom.modalTitle.textContent = title;
    dom.modalMessage.textContent = message;
    dom.modal.style.display = 'flex';
    currentModalCallback = callback;
    
    // 绑定确认按钮
    dom.modalConfirm.onclick = () => {
        if (currentModalCallback) {
            currentModalCallback();
        }
        hideModal();
    };
}

// 隐藏模态框
function hideModal() {
    dom.modal.style.display = 'none';
    currentModalCallback = null;
}

// 显示提示框
let toastTimeout = null;

function showToast(message, type = 'info') {
    if (toastTimeout) {
        clearTimeout(toastTimeout);
    }
    
    dom.toast.textContent = message;
    dom.toast.className = `toast ${type} show`;
    
    toastTimeout = setTimeout(() => {
        dom.toast.classList.remove('show');
    }, 3000);
}

// 工具函数
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(timestamp) {
    if (!timestamp) return '未知';
    
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}
