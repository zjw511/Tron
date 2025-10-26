/**
 * 表格预览前端组件
 * 在ComfyUI界面中显示交互式表格
 */

(function() {
    'use strict';
    
    console.log('[TablePreview] Loading table preview extension...');
    
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
                            showTableModal(output.table[0]);
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
     * 显示表格模态框
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
    
    console.log('[TablePreview] Table preview extension loaded!');
    
})();

