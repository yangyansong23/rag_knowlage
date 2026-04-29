// 全局变量
let currentConfig = {};
let referencesVisible = true;

// DOM 元素
const dom = {
    // 标签切换
    tabButtons: document.querySelectorAll('.tab-button'),
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
    rebuildDbBtn: document.getElementById('rebuildDbBtn'),
    clearDbBtn: document.getElementById('clearDbBtn'),
    
    // 配置
    kbPath: document.getElementById('kbPath'),
    vectorDbPath: document.getElementById('vectorDbPath'),
    chunkSize: document.getElementById('chunkSize'),
    chunkOverlap: document.getElementById('chunkOverlap'),
    retrieverTopK: document.getElementById('retrieverTopK'),
    saveConfigBtn: document.getElementById('saveConfigBtn'),
    currentConfigDisplay: document.getElementById('currentConfigDisplay'),
    
    // 聊天
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    charCount: document.getElementById('charCount'),
    
    // 参考资料
    referencesPanel: document.getElementById('referencesPanel'),
    referencesContent: document.getElementById('referencesContent'),
    toggleReferencesBtn: document.getElementById('toggleReferencesBtn'),
    
    // 状态显示
    fileCount: document.getElementById('fileCount'),
    dbStatus: document.getElementById('dbStatus'),
    
    // 提示框
    toast: document.getElementById('toast'),
    
    // 模态框
    confirmModal: document.getElementById('confirmModal'),
    modalTitle: document.getElementById('modalTitle'),
    modalMessage: document.getElementById('modalMessage'),
    modalCancelBtn: document.getElementById('modalCancelBtn'),
    modalConfirmBtn: document.getElementById('modalConfirmBtn')
};

// 初始化
document.addEventListener('DOMContentLoaded', init);

function init() {
    // 初始化标签切换
    initTabs();
    
    // 初始化文件上传
    initFileUpload();
    
    // 初始化聊天功能
    initChat();
    
    // 初始化参考资料面板
    initReferencesPanel();
    
    // 初始化事件监听
    initEventListeners();
    
    // 加载初始数据
    loadConfig();
    loadFileList();
    checkHealth();
}

// 标签切换
function initTabs() {
    dom.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;
            
            // 更新按钮状态
            dom.tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // 更新内容显示
            dom.tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });
}

// 文件上传
function initFileUpload() {
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
    // 输入字数统计
    dom.chatInput.addEventListener('input', () => {
        const count = dom.chatInput.value.length;
        dom.charCount.textContent = `${count}/2000`;
        
        // 自动调整高度
        dom.chatInput.style.height = 'auto';
        dom.chatInput.style.height = Math.min(dom.chatInput.scrollHeight, 120) + 'px';
    });
    
    // 发送按钮
    dom.sendBtn.addEventListener('click', sendMessage);
    
    // 键盘事件
    dom.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// 参考资料面板
function initReferencesPanel() {
    dom.toggleReferencesBtn.addEventListener('click', () => {
        referencesVisible = !referencesVisible;
        dom.referencesContent.style.display = referencesVisible ? 'block' : 'none';
        dom.toggleReferencesBtn.textContent = referencesVisible ? '收起' : '展开';
    });
}

// 事件监听
function initEventListeners() {
    // 刷新文件列表
    dom.refreshFilesBtn.addEventListener('click', loadFileList);
    
    // 保存配置
    dom.saveConfigBtn.addEventListener('click', saveConfig);
    
    // 重建数据库
    dom.rebuildDbBtn.addEventListener('click', () => {
        showConfirmModal(
            '确认重建数据库',
            '这将清空当前向量数据库并重新处理所有文件。此操作可能需要一些时间。确定继续吗？',
            rebuildDatabase
        );
    });
    
    // 清空数据库
    dom.clearDbBtn.addEventListener('click', () => {
        showConfirmModal(
            '确认清空数据库',
            '这将清空当前向量数据库中的所有数据。此操作不可撤销。确定继续吗？',
            clearDatabase
        );
    });
    
    // 模态框按钮
    dom.modalCancelBtn.addEventListener('click', hideConfirmModal);
}

// API 调用函数
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    try {
        const response = await fetch(url, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || '请求失败');
        }
        
        return data;
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}

// 加载配置
async function loadConfig() {
    try {
        const response = await apiRequest('/api/config');
        if (response.success) {
            currentConfig = response.data;
            updateConfigUI();
        }
    } catch (error) {
        showToast('加载配置失败: ' + error.message, 'error');
    }
}

// 更新配置UI
function updateConfigUI() {
    // 更新输入框
    dom.kbPath.value = currentConfig.knowledge_base_path || '';
    dom.vectorDbPath.value = currentConfig.vector_db_path || '';
    dom.chunkSize.value = currentConfig.chunk_size || 1000;
    dom.chunkOverlap.value = currentConfig.chunk_overlap || 200;
    dom.retrieverTopK.value = currentConfig.retriever_top_k || 3;
    
    // 更新当前配置显示
    dom.currentConfigDisplay.innerHTML = `
        <p><strong>知识库路径:</strong> ${currentConfig.knowledge_base_path}</p>
        <p><strong>向量数据库路径:</strong> ${currentConfig.vector_db_path}</p>
        <p><strong>集合名称:</strong> ${currentConfig.vector_db_collection_name}</p>
        <p><strong>分块大小:</strong> ${currentConfig.chunk_size}</p>
        <p><strong>重叠大小:</strong> ${currentConfig.chunk_overlap}</p>
        <p><strong>检索数量:</strong> ${currentConfig.retriever_top_k}</p>
        <p><strong>嵌入模型:</strong> ${currentConfig.embedding_model_name}</p>
        <p><strong>LLM模型:</strong> ${currentConfig.llm_model_name}</p>
    `;
}

// 保存配置
async function saveConfig() {
    const configData = {
        knowledge_base_path: dom.kbPath.value || undefined,
        vector_db_path: dom.vectorDbPath.value || undefined,
        chunk_size: parseInt(dom.chunkSize.value) || undefined,
        chunk_overlap: parseInt(dom.chunkOverlap.value) || undefined,
        retriever_top_k: parseInt(dom.retrieverTopK.value) || undefined
    };
    
    // 移除undefined值
    Object.keys(configData).forEach(key => {
        if (configData[key] === undefined) {
            delete configData[key];
        }
    });
    
    if (Object.keys(configData).length === 0) {
        showToast('没有需要保存的更改', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/api/config', {
            method: 'PUT',
            body: JSON.stringify(configData)
        });
        
        if (response.success) {
            showToast('配置保存成功', 'success');
            loadConfig(); // 重新加载配置
        }
    } catch (error) {
        showToast('保存配置失败: ' + error.message, 'error');
    }
}

// 加载文件列表
async function loadFileList() {
    try {
        const response = await apiRequest('/api/files');
        
        if (response.success) {
            const files = response.data.files || [];
            
            // 更新文件数量显示
            dom.fileCount.textContent = `${response.data.total_count || 0} 个文件`;
            
            // 更新文件列表
            if (files.length === 0) {
                dom.fileList.innerHTML = '<p class="empty-message">暂无文件</p>';
            } else {
                dom.fileList.innerHTML = files.map(file => `
                    <div class="file-item" data-file="${file.name}">
                        <div class="file-info">
                            <div class="file-name">${file.name}</div>
                            <div class="file-meta">
                                ${formatFileSize(file.size)} | ${formatDate(file.modified_time)}
                            </div>
                        </div>
                        <button class="btn btn-danger delete-btn" onclick="deleteFile('${file.name}')">删除</button>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
        dom.fileList.innerHTML = '<p class="empty-message">加载失败，请刷新重试</p>';
    }
}

// 上传文件
async function uploadFiles(files) {
    if (files.length === 0) return;
    
    // 显示上传进度
    dom.uploadProgress.style.display = 'block';
    dom.progressFill.style.width = '0%';
    dom.uploadStatus.textContent = '正在上传...';
    
    // 禁用上传区域
    dom.uploadArea.style.pointerEvents = 'none';
    
    const formData = new FormData();
    
    // 添加文件到FormData
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
            loadFileList(); // 刷新文件列表
        } else {
            dom.uploadStatus.textContent = '上传失败';
            showToast(data.message || '上传失败', 'error');
        }
    } catch (error) {
        dom.uploadStatus.textContent = '上传失败';
        showToast('上传失败: ' + error.message, 'error');
    } finally {
        // 重置上传区域
        setTimeout(() => {
            dom.uploadProgress.style.display = 'none';
            dom.uploadArea.style.pointerEvents = 'auto';
            dom.fileInput.value = '';
        }, 1500);
    }
}

// 删除文件
async function deleteFile(fileName) {
    showConfirmModal(
        '确认删除文件',
        `确定要删除文件 "${fileName}" 吗？注意：这只删除原始文件，向量数据库中的数据需要重新生成。`,
        async () => {
            try {
                const response = await apiRequest(`/api/files/${encodeURIComponent(fileName)}`, {
                    method: 'DELETE'
                });
                
                if (response.success) {
                    showToast(response.message, 'success');
                    loadFileList(); // 刷新文件列表
                }
            } catch (error) {
                showToast('删除失败: ' + error.message, 'error');
            }
        }
    );
}

// 重建数据库
async function rebuildDatabase() {
    hideConfirmModal();
    showToast('正在重建数据库，请稍候...', 'info');
    
    try {
        const response = await apiRequest('/api/rebuild', {
            method: 'POST'
        });
        
        if (response.success) {
            showToast(response.message, 'success');
            loadFileList();
        }
    } catch (error) {
        showToast('重建数据库失败: ' + error.message, 'error');
    }
}

// 清空数据库
async function clearDatabase() {
    hideConfirmModal();
    
    try {
        const response = await apiRequest('/api/database', {
            method: 'DELETE'
        });
        
        if (response.success) {
            showToast('数据库已清空', 'success');
        }
    } catch (error) {
        showToast('清空数据库失败: ' + error.message, 'error');
    }
}

// 发送消息
async function sendMessage() {
    const question = dom.chatInput.value.trim();
    
    if (!question) {
        showToast('请输入问题', 'warning');
        return;
    }
    
    // 添加用户消息到聊天区域
    addMessage(question, 'user');
    
    // 清空输入框
    dom.chatInput.value = '';
    dom.charCount.textContent = '0/2000';
    dom.chatInput.style.height = 'auto';
    
    // 显示加载动画
    const loadingId = addLoadingMessage();
    
    try {
        const response = await apiRequest('/api/chat', {
            method: 'POST',
            body: JSON.stringify({ question: question })
        });
        
        // 移除加载动画
        removeLoadingMessage(loadingId);
        
        if (response.success) {
            // 添加助手回答
            addMessage(response.data.answer, 'assistant');
            
            // 显示参考资料
            if (response.data.sources && response.data.sources.length > 0) {
                showReferences(response.data.sources);
            }
        } else {
            addMessage('抱歉，处理您的问题时出现错误。', 'assistant');
        }
    } catch (error) {
        removeLoadingMessage(loadingId);
        addMessage('抱歉，发生了错误: ' + error.message, 'assistant');
        showToast('查询失败: ' + error.message, 'error');
    }
}

// 添加消息到聊天区域
function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 处理换行符
    const formattedContent = content
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    contentDiv.innerHTML = `<p>${formattedContent}</p>`;
    messageDiv.appendChild(contentDiv);
    
    dom.chatMessages.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

// 添加加载动画
function addLoadingMessage() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant-message';
    loadingDiv.id = `loading-${Date.now()}`;
    
    loadingDiv.innerHTML = `
        <div class="loading-message">
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
function removeLoadingMessage(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// 显示参考资料
function showReferences(sources) {
    dom.referencesPanel.style.display = 'flex';
    referencesVisible = true;
    dom.referencesContent.style.display = 'block';
    dom.toggleReferencesBtn.textContent = '收起';
    
    dom.referencesContent.innerHTML = sources.map((source, index) => `
        <div class="reference-item">
            <div class="reference-source">
                参考资料 ${index + 1}: ${source.metadata.source || '未知来源'}
            </div>
            <div class="reference-content">
                ${source.content.substring(0, 300)}${source.content.length > 300 ? '...' : ''}
            </div>
        </div>
    `).join('');
}

// 滚动到底部
function scrollToBottom() {
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// 健康检查
async function checkHealth() {
    try {
        const response = await apiRequest('/api/health');
        if (response.status === 'healthy') {
            dom.dbStatus.textContent = '数据库: 正常';
        }
    } catch (error) {
        dom.dbStatus.textContent = '数据库: 连接失败';
        console.error('健康检查失败:', error);
    }
}

// 显示确认模态框
let confirmCallback = null;

function showConfirmModal(title, message, callback) {
    dom.modalTitle.textContent = title;
    dom.modalMessage.textContent = message;
    dom.confirmModal.style.display = 'flex';
    confirmCallback = callback;
    
    // 绑定确认按钮
    dom.modalConfirmBtn.onclick = () => {
        if (confirmCallback) {
            confirmCallback();
        }
        hideConfirmModal();
    };
}

function hideConfirmModal() {
    dom.confirmModal.style.display = 'none';
    confirmCallback = null;
}

// 显示提示框
let toastTimeout = null;

function showToast(message, type = 'info') {
    // 清除之前的计时器
    if (toastTimeout) {
        clearTimeout(toastTimeout);
    }
    
    // 设置内容和类型
    dom.toast.textContent = message;
    dom.toast.className = `toast ${type} show`;
    
    // 3秒后隐藏
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

// 暴露全局函数
window.deleteFile = deleteFile;
