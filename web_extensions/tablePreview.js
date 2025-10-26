/**
 * 表格预览前端组件
 * 在ComfyUI界面中显示交互式表格
 */

(function() {
    'use strict';
    
    console.log('[TablePreview] Loading table preview extension...');
    
    // 暴露showTableModal到全局，供"在弹窗中查看"链接使用
    window.showTableModal = null;
    
    // 等待DOM加载完成
    function waitForComfyUI() {
        return new Promise((resolve) => {
            if (window.comfyAPI || window.app) {
                resolve();
            } else {
                const checkInterval = setInterval(() => {
                    if (window.comfyAPI || window.app) {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 100);
                
                // 超时后也继续
                setTimeout(() => {
                    clearInterval(checkInterval);
                    resolve();
                }, 5000);
            }
        });
    }
    
    // 初始化扩展
    waitForComfyUI().then(() => {
        console.log('[TablePreview] ComfyUI loaded, registering extension...');
        
        // 尝试使用ComfyUI的扩展API
        const api = window.comfyAPI || window.api;
        
        if (api && typeof api.addEventListener === 'function') {
            // 使用事件监听方式
            console.log('[TablePreview] Using event-based API');
            
            api.addEventListener('executed', (e) => {
                const detail = e.detail || e;
                console.log('[TablePreview] Event received:', detail);
                
                // 检查table数据
                if (detail && detail.output && detail.output.table) {
                    console.log('[TablePreview] ✓ Found table data:', detail.output.table);
                    showTableModal(detail.output.table[0]);
                } else {
                    console.log('[TablePreview] ✗ No table in event:', detail);
                }
            });
            
        } else {
            // 回退到直接监听WebSocket消息
            console.log('[TablePreview] Using direct monitoring');
            monitorWebSocketMessages();
        }
    });
    
    /**
     * 监听WebSocket消息（回退方案）
     */
    function monitorWebSocketMessages() {
        // 拦截WebSocket
        const OriginalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            const ws = new OriginalWebSocket(url, protocols);
            
            ws.addEventListener('message', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // 调试：打印所有消息类型
                    if (data.type) {
                        console.log('[TablePreview] WS message type:', data.type, data);
                    }
                    
                    // 检查是否是执行完成消息
                    if (data.type === 'executed' || data.type === 'execution_cached') {
                        console.log('[TablePreview] Execution message:', data);
                        
                        const output = data.data?.output;
                        console.log('[TablePreview] Output data:', output);
                        
                        // 检查table数据（直接在output中，不在ui子对象中）
                        if (output && output.table) {
                            console.log('[TablePreview] ✓ Found table data:', output.table);
                            // 不自动弹窗，而是渲染到节点上
                            renderTableInNode(data.data.node, output.table[0]);
                        } else {
                            console.log('[TablePreview] ✗ No table data in output');
                            console.log('[TablePreview]   output:', output);
                            console.log('[TablePreview]   output.table:', output?.table);
                        }
                    }
                } catch (e) {
                    // 忽略非JSON消息
                }
            });
            
            return ws;
        };
        
        console.log('[TablePreview] WebSocket monitoring active');
    }
    
    /**
     * 在节点中渲染表格（类似PreviewImage）
     */
    function renderTableInNode(nodeId, tableData) {
        if (!tableData) return;
        
        console.log('[TablePreview] Rendering table in node:', nodeId);
        console.log('[TablePreview] Table data:', tableData);
        
        // 创建表格容器
        const containerId = `table-preview-${nodeId}`;
        let container = document.getElementById(containerId);
        
        if (!container) {
            // 创建新容器
            container = document.createElement('div');
            container.id = containerId;
            container.className = 'comfy-table-preview';
            container.style.cssText = `
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: #1e1e1e;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 15px;
                overflow: auto;
                max-height: 500px;
                max-width: 900px;
                min-width: 600px;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            `;
            
            console.log('[TablePreview] Creating new container with ID:', containerId);
            
            // 直接添加到body，使用fixed定位确保可见
            document.body.appendChild(container);
            console.log('[TablePreview] Container appended to body');
        } else {
            console.log('[TablePreview] Reusing existing container');
        }
        
        // 渲染表格HTML
        const tableHTML = `
            <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #fff;">${escapeHtml(tableData.title)}</strong>
                    <span style="color: #aaa; margin-left: 10px;">
                        ${tableData.shape[0]} rows × ${tableData.shape[1]} columns
                    </span>
                </div>
                <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                        style="background:#444;border:none;color:#fff;padding:4px 12px;border-radius:3px;cursor:pointer;">
                    关闭
                </button>
            </div>
            ${tableData.truncated ? `
                <div style="background: #443300; padding: 6px; border-radius: 3px; margin-bottom: 8px; color: #ffcc00; font-size: 12px;">
                    ⚠ 显示前 ${tableData.total_rows} 行
                </div>
            ` : ''}
            <div style="overflow: auto; max-height: 350px;">
                <table style="width: 100%; border-collapse: collapse; font-family: monospace; font-size: 11px;">
                    <thead>
                        <tr style="background: #2a2a2a; position: sticky; top: 0;">
                            <th style="padding: 6px; border: 1px solid #444; color: #aaa; text-align: center;">#</th>
                            ${tableData.columns.map(col => `
                                <th style="padding: 6px; border: 1px solid #444; color: #fff; text-align: left;">
                                    ${escapeHtml(col)}
                                    <br>
                                    <span style="color: #888; font-size: 9px;">${tableData.dtypes[col] || ''}</span>
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${tableData.data.slice(0, 20).map((row, idx) => `
                            <tr style="background: ${idx % 2 === 0 ? '#1a1a1a' : '#242424'};">
                                <td style="padding: 6px; border: 1px solid #444; color: #888; text-align: center;">${idx}</td>
                                ${row.map(cell => `
                                    <td style="padding: 6px; border: 1px solid #444; color: #ddd;">
                                        ${escapeHtml(formatCell(cell))}
                                    </td>
                                `).join('')}
                            </tr>
                        `).join('')}
                        ${tableData.data.length > 20 ? `
                            <tr>
                                <td colspan="${tableData.columns.length + 1}" style="padding: 8px; text-align: center; color: #888; background: #2a2a2a;">
                                    ... 还有 ${tableData.data.length - 20} 行
                                    <button id="show-all-btn-${containerId}" style="margin-left: 10px; background:#555;border:none;color:#fff;padding:3px 10px;border-radius:3px;cursor:pointer;">
                                        显示全部
                                    </button>
                                </td>
                            </tr>
                        ` : ''}
                    </tbody>
                </table>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #888;">
                Node ID: ${nodeId} | 
                <a href="#" id="show-modal-link-${containerId}" style="color: #6af; text-decoration: none;">
                    在弹窗中查看
                </a>
            </div>
        `;
        
        console.log('[TablePreview] Setting innerHTML...');
        container.innerHTML = tableHTML;
        console.log('[TablePreview] innerHTML set, container visible:', container.offsetHeight > 0);
        
        // 添加"显示全部"按钮事件
        const showAllBtn = document.getElementById(`show-all-btn-${containerId}`);
        if (showAllBtn) {
            console.log('[TablePreview] Attaching show-all button');
            showAllBtn.onclick = () => {
                const tbody = container.querySelector('tbody');
                tbody.innerHTML = generateAllRowsHTML(tableData);
            };
        }
        
        // 添加"在弹窗中查看"链接事件
        const showModalLink = document.getElementById(`show-modal-link-${containerId}`);
        if (showModalLink) {
            console.log('[TablePreview] Attaching modal link');
            showModalLink.onclick = (e) => {
                e.preventDefault();
                showTableModal(tableData);
            };
        }
        
        console.log('[TablePreview] ✓ Table rendered successfully!');
        console.log('[TablePreview] Container position:', container.getBoundingClientRect());
    }
    
    /**
     * 生成所有行的HTML
     */
    function generateAllRowsHTML(tableData) {
        return tableData.data.map((row, idx) => `
            <tr style="background: ${idx % 2 === 0 ? '#1a1a1a' : '#242424'};">
                <td style="padding: 6px; border: 1px solid #444; color: #888; text-align: center;">${idx}</td>
                ${row.map(cell => `
                    <td style="padding: 6px; border: 1px solid #444; color: #ddd;">
                        ${escapeHtml(formatCell(cell))}
                    </td>
                `).join('')}
            </tr>
        `).join('');
    }
    
    /**
     * 显示表格模态框（作为备选功能）
     */
    function showTableModal(tableData) {
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'comfy-table-modal';
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #1e1e1e;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 20px;
            z-index: 10000;
            max-width: 90vw;
            max-height: 90vh;
            overflow: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;
        
        // 创建表格HTML
        const html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0; color: #fff;">${tableData.title}</h3>
                <div>
                    <span style="color: #aaa; margin-right: 15px;">
                        ${tableData.shape[0]} rows × ${tableData.shape[1]} columns
                    </span>
                    <button id="closeTableBtn" style="
                        background: #444;
                        border: none;
                        color: #fff;
                        padding: 5px 15px;
                        border-radius: 4px;
                        cursor: pointer;
                    ">关闭</button>
                </div>
            </div>
            ${tableData.truncated ? `
                <div style="background: #443300; padding: 8px; border-radius: 4px; margin-bottom: 10px; color: #ffcc00;">
                    ⚠ 显示前 ${tableData.total_rows} 行
                </div>
            ` : ''}
            <div style="overflow: auto; max-height: calc(90vh - 120px);">
                <table style="
                    width: 100%;
                    border-collapse: collapse;
                    font-family: monospace;
                    font-size: 12px;
                ">
                    <thead>
                        <tr style="background: #2a2a2a; position: sticky; top: 0;">
                            <th style="padding: 8px; border: 1px solid #444; color: #aaa;">#</th>
                            ${tableData.columns.map(col => `
                                <th style="padding: 8px; border: 1px solid #444; color: #fff; text-align: left;">
                                    ${escapeHtml(col)}
                                    <br>
                                    <span style="color: #888; font-size: 10px;">${tableData.dtypes[col] || ''}</span>
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${tableData.data.map((row, idx) => `
                            <tr style="background: ${idx % 2 === 0 ? '#1a1a1a' : '#242424'};">
                                <td style="padding: 8px; border: 1px solid #444; color: #888;">${idx}</td>
                                ${row.map(cell => `
                                    <td style="padding: 8px; border: 1px solid #444; color: #ddd;">
                                        ${escapeHtml(formatCell(cell))}
                                    </td>
                                `).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        modal.innerHTML = html;
        
        // 添加到页面
        document.body.appendChild(modal);
        
        // 添加背景遮罩
        const overlay = document.createElement('div');
        overlay.className = 'comfy-table-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.7);
            z-index: 9999;
        `;
        document.body.appendChild(overlay);
        
        // 关闭事件
        const closeModal = () => {
            modal.remove();
            overlay.remove();
        };
        
        document.getElementById('closeTableBtn').onclick = closeModal;
        overlay.onclick = closeModal;
        
        // ESC键关闭
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }
    
    /**
     * 格式化单元格内容
     */
    function formatCell(value) {
        if (value === null || value === undefined) {
            return '<span style="color: #666;">null</span>';
        }
        if (typeof value === 'number') {
            // 格式化数字
            if (Number.isInteger(value)) {
                return value.toString();
            } else {
                return value.toFixed(4);
            }
        }
        if (typeof value === 'boolean') {
            return `<span style="color: ${value ? '#0f0' : '#f00'};">${value}</span>`;
        }
        return String(value);
    }
    
    /**
     * HTML转义
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 暴露showTableModal到全局
    window.showTableModal = showTableModal;
    
    console.log('[TablePreview] Table preview extension loaded!');
    
})();

