# ComfyUI 简化版

> 完整功能的ComfyUI服务器 - 使用官方前端 + 模块化节点系统

## 🚀 快速开始

### 方法1：一键启动（推荐）

```bash
# Windows
双击 START_FULL.bat

# 或命令行
python full_server.py
```

### 方法2：访问地址

浏览器打开：`http://127.0.0.1:8188`

## 📦 安装依赖

首次使用需要安装依赖：

```bash
pip install -r requirements.txt
```

主要依赖：
- `aiohttp` - 异步Web服务器
- `Pillow` - 图片处理
- `comfyui-frontend-package` - ComfyUI官方前端界面

## 📁 项目结构

```
simple_comfyui/
├── full_server.py          # 完整功能服务器（推荐使用）⭐
├── nodes.py                # 节点定义系统
├── requirements.txt        # Python依赖列表
├── START_FULL.bat          # 快速启动脚本
│
├── simple_server.py        # 简化版服务器（备用）
├── modular_server.py       # 模块化服务器（备用）
├── start_modular.bat       # 模块化启动脚本
│
├── README.md               # 本文件
├── 使用指南.md             # 详细使用说明
├── 项目说明.md             # 项目总览
├── FULL_FEATURES.md        # 完整功能文档（英文）
│
├── input/                  # 输入图片目录
├── output/                 # 输出结果目录
└── temp/                   # 临时预览目录
```

## ✨ 功能特点

### ✅ 完整的节点系统

支持12种节点类型：

| 节点类型 | 功能说明 |
|---------|---------|
| `LoadImage` | 加载图片 |
| `SaveImage` | 保存图片 |
| `ImageScale` | 图片缩放 |
| `PreviewImage` | 实时预览图片 |
| `PrimitiveFloat` | 浮点数输入 |
| `PrimitiveString` | 字符串输入 |
| `LatentBlend` | 潜在空间混合 |
| `VAEDecode` | VAE解码 |
| `PreviewAny` | 预览任意类型 |
| `Reroute` | 重路由连接 |
| `Note` | 添加注释 |
| `MarkdownNote` | Markdown注释 |

### ✅ 工作流执行引擎

- **拓扑排序** - 自动按依赖关系排序节点
- **智能数据传递** - 自动匹配输入输出类型
- **错误处理** - 完整的异常捕获和报告
- **循环依赖检测** - 防止无限循环

### ✅ WebSocket实时通信

- 实时连接管理
- 广播消息系统
- `executed` 事件推送
- 图片预览实时显示

### ✅ 完整的API支持

23个完整的API端点，兼容ComfyUI标准：

**核心API:**
- `POST /prompt` - 执行工作流
- `GET /object_info` - 获取节点信息
- `GET /queue` - 队列状态
- `GET /history` - 历史记录
- `GET /system_stats` - 系统状态
- `GET /ws` - WebSocket连接

**用户API:**
- `GET/POST /users` - 用户管理
- `GET/POST /settings` - 设置管理
- `GET /userdata` - 用户数据

**图片API:**
- `GET /view` - 查看图片

## 🎯 使用示例

### 示例1：图片预览

```
1. 添加 LoadImage 节点
2. 添加 PreviewImage 节点
3. 连接：LoadImage → PreviewImage
4. 点击 "Queue Prompt" 运行
5. 图片会实时显示在PreviewImage节点中
```

### 示例2：图片缩放保存

```
1. 添加 LoadImage 节点
2. 添加 ImageScale 节点（设置宽高512x512）
3. 添加 SaveImage 节点
4. 连接：LoadImage → ImageScale → SaveImage
5. 运行后查看 output/ 目录
```

### 示例3：多输出工作流

```
LoadImage → ImageScale → PreviewImage
          ↓
       SaveImage
```

## 📊 版本对比

| 特性 | full_server.py | simple_server.py | modular_server.py |
|------|---------------|------------------|-------------------|
| 节点系统 | ✅ 模块化（nodes.py） | ⚠️ 硬编码 | ✅ 模块化 |
| 执行引擎 | ✅ 完整拓扑排序 | ⚠️ 简化版 | ✅ 完整 |
| WebSocket | ✅ 完整广播系统 | ⚠️ 基础 | ✅ 完整 |
| 图片预览 | ✅ 实时预览 | ❌ 无 | ✅ 实时预览 |
| 错误处理 | ✅ 完整追踪 | ⚠️ 基础 | ✅ 完整 |
| 历史记录 | ✅ 有 | ❌ 无 | ✅ 有 |
| 调试日志 | ✅ 详细 | ⚠️ 少 | ✅ 详细 |
| API端点 | ✅ 23个 | ⚠️ 15个 | ✅ 23个 |
| **推荐用途** | **生产使用** | 学习理解 | 开发调试 |

## 🐛 常见问题

### Q: 端口8188被占用？

```bash
# Windows PowerShell
Get-Process python | Stop-Process -Force
```

### Q: 页面空白或404错误？

1. 确认已安装 `comfyui-frontend-package`
2. 强制刷新浏览器：`Ctrl+Shift+R`
3. 检查服务器日志

### Q: 图片不显示？

1. 检查 `input/` 目录是否有图片
2. 查看浏览器Console错误（F12）
3. 查看服务器控制台日志

### Q: 节点执行失败？

查看服务器控制台的详细错误信息：
- `[>>]` - 信息日志
- `[*]` - 执行日志
- `[OK]` - 成功日志
- `[X]` - 错误日志

## 🔧 开发说明

### 添加自定义节点

在 `nodes.py` 中：

```python
class MyCustomNode(NodeBase):
    def __init__(self):
        super().__init__()
        self.name = "MyCustomNode"
        self.category = "custom"
        
    def get_node_info(self):
        return {
            "input": {"required": {"input": ["STRING", {}]}},
            "output": ["STRING"],
            # ...
        }
    
    def execute(self, inputs, node_id):
        # 你的逻辑
        return {"STRING": result}
```

节点会自动注册到系统！

### 修改端口

在 `full_server.py` 中修改：

```python
site = web.TCPSite(runner, '127.0.0.1', 8188)
#                                        ^^^^
#                                        改这里
```

## 📖 文档

- **README.md** - 本文件（快速开始）
- **使用指南.md** - 详细使用说明
- **项目说明.md** - 项目结构和状态
- **FULL_FEATURES.md** - 完整功能文档（英文）

## ⚠️ 注意事项

1. **不要删除核心文件**：
   - `full_server.py`
   - `nodes.py`
   - `requirements.txt`

2. 首次运行需要安装依赖

3. 确保端口8188未被占用

4. `input/` 目录需要有测试图片

5. 使用 `Ctrl+C` 正常停止服务器

## 🎯 技术栈

**后端：**
- Python 3.11+
- aiohttp (异步Web服务器)
- Pillow (图片处理)

**前端：**
- comfyui_frontend_package (官方前端)
- LiteGraph.js (节点编辑器)
- WebSocket (实时通信)

## 📝 更新日志

### v1.0.0 (2025-10-26)

- ✅ 完整的节点系统（12种节点）
- ✅ 拓扑排序执行引擎
- ✅ WebSocket实时通信
- ✅ 图片预览功能
- ✅ 23个完整API端点
- ✅ 中文界面支持
- ✅ 详细文档

## 📞 支持

遇到问题？

1. 查看 [使用指南.md](使用指南.md)
2. 查看 [FULL_FEATURES.md](FULL_FEATURES.md)
3. 检查服务器日志
4. 检查浏览器Console（F12）

---

**祝使用愉快！** 🎉

