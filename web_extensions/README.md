# Web Extensions 目录

这个目录用于存放ComfyUI的前端扩展JavaScript文件。

## 📁 当前扩展

### tablePreview.js
表格数据预览扩展 - 在前端显示交互式表格

**功能**：
- 拦截PreviewTable节点的执行结果
- 显示交互式表格弹窗
- 支持暗色主题
- 自动格式化数据

## 🚀 如何使用

### 1. 扩展会自动加载

当你启动服务器时，`web_extensions`目录中的所有`.js`文件会被自动注入到前端页面中。

### 2. 查看加载状态

启动服务器时会显示：
```
[OK] Loaded web_extensions from: /path/to/web_extensions
[OK] Injected 1 extension script(s)
[>>] Web extensions: 1 file(s) loaded
```

### 3. 验证扩展已加载

打开浏览器，按F12打开控制台，应该看到：
```
[TablePreview] Loading table preview extension...
```

## 🔧 创建自定义扩展

### 基本模板

```javascript
/**
 * 我的自定义扩展
 */

(function() {
    'use strict';
    
    // 获取ComfyUI app实例
    const app = window.app || window.comfyAPI?.app;
    
    if (!app) {
        console.error('[MyExtension] ComfyUI app not found');
        return;
    }
    
    console.log('[MyExtension] Loading...');
    
    // 注册扩展
    app.registerExtension({
        name: "custom.myExtension",
        
        async beforeRegisterNodeDef(nodeType, nodeData, app) {
            // 在节点注册前修改节点行为
            if (nodeData.name === "MyNodeName") {
                console.log('[MyExtension] Found MyNodeName');
                // 自定义逻辑...
            }
        },
        
        async setup(app) {
            // 在ComfyUI初始化时运行
            console.log('[MyExtension] Setup complete');
        }
    });
})();
```

### 扩展放置位置

将`.js`文件直接放在`web_extensions/`目录中：
```
web_extensions/
├── tablePreview.js      # 表格预览扩展
├── myCustom.js          # 你的自定义扩展
└── README.md            # 本文档
```

### 加载顺序

扩展按字母顺序加载。如果需要特定顺序，可以使用前缀：
```
01_base.js
02_advanced.js
```

## 🐛 故障排除

### Q: 扩展没有加载？

1. **检查服务器日志**：
   ```
   [OK] Loaded web_extensions from: ...
   [OK] Injected X extension script(s)
   ```

2. **检查文件位置**：
   - 确保文件在`web_extensions/`目录
   - 确保文件扩展名是`.js`

3. **检查浏览器控制台**（F12）：
   - 查看是否有加载错误
   - 查看是否有JavaScript错误

### Q: 404错误？

**解决方案**：
1. 重启服务器（Ctrl+C 然后重新运行）
2. 强制刷新浏览器（Ctrl+Shift+R）
3. 检查`web_extensions/`目录是否存在

### Q: 扩展代码有错误？

打开浏览器控制台（F12）查看详细错误信息。

### Q: 修改扩展后没有生效？

1. 重启服务器
2. 强制刷新浏览器（Ctrl+Shift+R）
3. 清除浏览器缓存

## 📚 ComfyUI扩展API

### 常用钩子

```javascript
app.registerExtension({
    name: "your.extension",
    
    // 在节点注册前
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // 修改节点定义
    },
    
    // 在节点注册后
    async nodeCreated(node) {
        // 节点创建后的处理
    },
    
    // 在初始化时
    async setup(app) {
        // 应用初始化
    },
    
    // 添加自定义菜单
    async getCustomWidgets(app) {
        return {
            "MY_WIDGET": (node, inputName, inputData, app) => {
                // 返回自定义widget
            }
        };
    }
});
```

### 节点事件

```javascript
// 重写节点的onExecuted方法
const onExecuted = nodeType.prototype.onExecuted;
nodeType.prototype.onExecuted = function(message) {
    // 调用原始方法
    if (onExecuted) {
        onExecuted.apply(this, arguments);
    }
    
    // 处理执行结果
    if (message?.output_data) {
        console.log('Node output:', message.output_data);
    }
};
```

## 📊 示例：表格预览扩展

查看`tablePreview.js`了解完整示例，它展示了如何：
- 注册扩展
- 拦截节点执行
- 创建自定义UI（模态框）
- 处理节点输出数据

## 🔗 资源链接

- [ComfyUI官方文档](https://github.com/comfyanonymous/ComfyUI)
- [表格节点文档](../docs/TABLE_NODES_README.md)
- [项目README](../README.md)

---

**提示**：扩展文件会被自动加载，无需手动配置！

