/**
 * 表格预览前端组件
 * 在ComfyUI界面中显示交互式表格
 */

(function() {
    'use strict';
    
    // 等待ComfyUI加载完成
    const app = window.app || window.comfyAPI?.app;
    
    if (!app) {
        console.error('[TablePreview] ComfyUI app not found');
        return;
    }
    
    console.log('[TablePreview] Loading table preview extension...');
    
    // 注册自定义widget类型
    app.registerExtension({
        name: "comfy.tablePreview",
        
        async beforeRegisterNodeDef(nodeType, nodeData, app) {
            // 只处理PreviewTable节点
            if (nodeData.name === "PreviewTable") {
                console.log('[TablePreview] Registering PreviewTable node');
                
                // 重写节点的onExecuted方法
                const onExecuted = nodeType.prototype.onExecuted;
                nodeType.prototype.onExecuted = function(message) {
                    // 调用原始方法
                    if (onExecuted) {
                        onExecuted.apply(this, arguments);
                    }
                    
                    // 处理表格数据
                    if (message?.table) {
                        console.log('[TablePreview] Received table data:', message.table);
                        renderTable(this, message.table[0]);
                    }
                };
            }
        }
    });
    
    /**
     * 渲染表格到节点
     */
    function renderTable(node, tableData) {
        if (!tableData) return;
        
        // 创建或获取表格容器
        let tableWidget = node.widgets?.find(w => w.name === "table_display");
        
        if (!tableWidget) {
            // 创建一个自定义widget
            tableWidget = {
                name: "table_display",
                type: "customWidget",
                value: "",
                draw: function(ctx, node, width, y) {
                    // 在canvas上绘制表格摘要
                    ctx.font = "12px monospace";
                    ctx.fillStyle = "#fff";
                    
                    const info = `${tableData.title} [${tableData.shape[0]}×${tableData.shape[1]}]`;
                    ctx.fillText(info, 10, y + 15);
                    
                    if (tableData.truncated) {
                        ctx.fillStyle = "#ff9";
                        ctx.fillText(`(showing first ${tableData.total_rows} rows)`, 10, y + 30);
                        return 45;
                    }
                    
                    return 25;
                },
                computeSize: function(width) {
                    return [width, tableData.truncated ? 45 : 25];
                }
            };
            
            node.addCustomWidget(tableWidget);
        }
        
        // 在节点上添加点击事件
        const originalOnMouseDown = node.onMouseDown;
        node.onMouseDown = function(e, pos, canvas) {
            // 检查是否点击在widget区域
            if (pos[1] > this.size[1] - 60) {
                showTableModal(tableData);
                return true;
            }
            
            if (originalOnMouseDown) {
                return originalOnMouseDown.call(this, e, pos, canvas);
            }
        };
        
        // 自动显示表格（第一次）
        if (!node._tableShown) {
            node._tableShown = true;
            setTimeout(() => showTableModal(tableData), 100);
        }
        
        // 调整节点大小
        node.setSize([Math.max(300, node.size[0]), node.size[1]]);
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

