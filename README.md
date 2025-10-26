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

### Q: 如何批量执行超过100次工作流？

前端 Queue Button 有100次限制。使用 `batch_queue_workflow.py` 绕过限制：

```bash
python batch_queue_workflow.py
```

**注意**：脚本需要**API格式**的工作流文件。

**获取API格式工作流的方法：**

1. **通过浏览器开发者工具（推荐）**：
   - 打开ComfyUI界面
   - 按F12打开开发者工具
   - 切换到 Network（网络）标签
   - 点击 'Queue Prompt' 执行一次工作流
   - 在Network中找到 `/prompt` 请求
   - 右键 → Copy → Copy Request Payload
   - 将内容保存为JSON文件（如 `workflow_api.json`）

2. **修改脚本使用新文件**：
```python
# 在 batch_queue_workflow.py 中修改
workflow = load_workflow("workflow_api.json")  # 使用你保存的文件
```

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

## 🎯 扩展功能：信号处理节点 (NEW!)

### 📡 通信信号处理系统 - 已完全集成！

**状态**: ✅ 已集成到ComfyUI  
**节点数**: 14个专用节点 + 6个基础节点 = 20个总节点  
**测试状态**: ✅ 全部通过

全新的信号处理节点系统，用于通信信号分析和可视化，**已完全集成到ComfyUI Web界面**！

**14个专用节点：**
- 📡 NetworkReceiver - 网络数据接收 (UDP/TCP)
- 📦 DataBuffer - 数据缓冲器
- 📊 BufferMonitor - 缓冲区监视器
- 🔍 FrameParser - 帧结构解析
- 🔄 DataConverter - 数据格式转换
- 📈 SpectrumAnalyzer - 频谱分析
- 🧭 AzimuthProcessor - 方位角处理
- 🎯 SignalClassifier - 信号类型识别
- 📶 FrequencyDetector - 频点检测
- ⏱️ SymbolRateAnalyzer - 符号速率分析
- ⭐ ConstellationDiagram - 星座图生成
- 📺 SignalMonitor - 信号监视器（控制台）
- 📋 **SignalInfoImage** - 信号信息面板（NEW! 浏览器显示）
- 💾 RawDataSaver - 原始数据保存

### 🚀 两种使用方式

#### 方式1: 在ComfyUI Web界面中使用（推荐）

```bash
# 1. 启动ComfyUI服务器
python full_server.py
# 或双击: START_FULL.bat

# 2. 打开浏览器
# http://127.0.0.1:8188

# 3. 在界面中添加信号处理节点
# 右键 → Add Node → signal/...
```

**预期输出**:
```
[OK] Signal processing nodes loaded successfully
[OK] Basic nodes: 6 个
[OK] Signal nodes: 13 个
[OK] Total nodes: 19
[>>] Server running at: http://127.0.0.1:8188
```

#### 方式2: 独立使用（命令行）

```bash
# 运行测试
python test_signal_nodes.py
# 或双击：测试信号节点.bat

# 运行示例
python signal_nodes_example.py
# 或双击：运行信号示例.bat
```

### 📡 实时数据发送器 (NEW!)

**持续向NetworkReceiver节点发送测试信号数据**

```bash
# Windows快速启动
双击: send_signal_data.bat

# 或命令行
python send_signal_data.py
```

**两种模式**:
- **快速启动**: 使用默认参数（QPSK, 127.0.0.1:8888, 1秒间隔）
- **交互模式**: 自定义信号类型、端口、间隔等参数

**支持信号类型**: QPSK, QAM16, FSK, ASK

**典型使用流程**:
```
1. 启动ComfyUI → 创建工作流 → 运行工作流
2. 启动数据发送器 → 观察实时显示
3. Ctrl+C 停止发送
```

详见: [SEND_SIGNAL_README.md](SEND_SIGNAL_README.md)

### 📖 完整文档

- 🌐 **[ComfyUI集成说明.md](ComfyUI集成说明.md)** - Web界面使用指南 ⭐ 必读
- 📖 [信号处理节点说明.md](信号处理节点说明.md) - 详细API文档
- 🚀 [快速开始_信号处理.md](快速开始_信号处理.md) - 快速入门
- 📋 [信号处理开发总结.md](信号处理开发总结.md) - 系统架构
- 🔧 [中文字体修复说明.md](中文字体修复说明.md) - 字体配置

### ✨ 特点

- ✅ **完全集成**: 在ComfyUI Web界面中直接使用
- ✅ **图形化操作**: 拖拽连接节点，可视化工作流
- ✅ **实时预览**: PreviewImage实时显示结果
- ✅ **持续运行**: 支持持续接收和并发执行
- ✅ **测试完整**: 7/7节点测试 + 16/16集成测试全通过
- ✅ **中文支持**: 自动配置中文字体（跨平台）
- ✅ **独立模块**: 不影响原有功能

### 🧪 快速验证集成

```bash
# 运行集成测试
python test_integration.py
```

预期输出:
```
✓ 基础节点数量: 6
✓ 信号处理节点数量: 13
✓ 总节点数: 19
✓ 所有测试通过
🎉 信号处理节点已成功集成到ComfyUI！
```

## 📝 更新日志

### v1.2.4 (2025-10-26)

- 🎨 **优化**: SignalInfoImage 中文字体显示（移除 monospace 限制）
- ✅ **改进**: 信号信息面板现在可以正确显示中文标题和字段名
- 📋 **完善**: 使用全局配置的中文字体（Microsoft YaHei）
- 💡 **说明**: 所有中文内容（中心频率、采样率、信号类型等）现在都能正常显示

### v1.2.3 (2025-10-26)

- 🔧 **修复**: SignalInfoImage 图像输出问题（现在正确返回 PIL Image 对象）
- 🔧 **修复**: 用户数据存储路径解析（支持查询参数和路径参数两种格式）
- ⚡ **优化**: 添加 `/userdata/{path:.*}` 路由支持多种URL格式
- ✅ **测试**: SignalInfoImage → PreviewImage 完全正常显示
- 💡 **说明**: 信号信息面板和工作流保存现在都可以正常使用了

### v1.2.2 (2025-10-26)

- 🔧 **修复**: 用户数据存储 405 错误 (workflows/signal.json 保存失败)
- ⚡ **优化**: 添加 POST 和 DELETE 路由支持
- ✅ **增强**: 工作流保存、读取、删除功能完全正常
- 💡 **说明**: 现在可以在浏览器中保存工作流了

### v1.2.1 (2025-10-26)

- ✨ **新增**: SignalInfoImage节点 - 信号信息在浏览器中显示 🎉
- 🌐 **功能**: 生成包含所有信号参数的图像面板
- 🎨 **功能**: 支持深色/浅色主题，可调节字体大小
- 💡 **优势**: 无需查看控制台，浏览器直接显示
- 📋 **内容**: 基本参数、信号特征、空间信息、元数据
- 📝 **文档**: 更新使用指南增加浏览器显示说明

### v1.2.0 (2025-10-26)

- ✨ **新增**: DataBuffer节点 - 数据缓冲管理器
- 📊 **新增**: BufferMonitor节点 - 实时监控缓冲区状态
- 🔍 **功能**: 缓存数据、队列管理、统计信息
- 📈 **可视化**: 4象限图表显示缓冲区详细状态
- 🎯 **模式**: 支持队列(FIFO)、栈(LIFO)、覆盖三种模式

### v1.1.4 (2025-10-26)

- ✨ **新增**: RawDataSaver节点 - 保存原始数据到文件
- 💾 **功能**: 支持二进制、十六进制、双格式保存
- 🔍 **调试**: 便于排查网络接收问题
- 📝 **格式**: 十六进制文件可用记事本直接查看

### v1.1.3 (2025-10-26)

- 🔧 **修复**: Windows UDP接收缓冲区错误 (WinError 10040)
- 🎯 **优化**: 默认缓冲区大小从4KB增大到64KB
- 💡 **增强**: 更友好的错误提示和解决建议
- ✅ **改进**: 持续接收模式不再因缓冲区错误而中断

### v1.1.2 (2025-10-26)

- 🔧 **修复**: NetworkReceiver节点线程重复创建问题
- 🎯 **优化**: 使用类级别接收器管理，确保同一配置只有一个线程
- 🔒 **增强**: 线程安全机制，防止竞态条件
- ⚡ **性能**: 显著降低资源占用，提升稳定性

### v1.1.1 (2025-10-26)

- 🔧 **修复**: 用户数据存储API (workflows/signal.json保存失败)
- ✨ **新增**: 完整的文件操作支持 (保存/加载/删除)
- ✨ **新增**: `user/` 目录用于存储工作流和配置
- 🔒 **增强**: 路径安全检查和错误处理

### v1.1.0 (2025-10-26)

- ✨ **新增**: 信号处理节点系统（10个专用节点）
- ✨ **新增**: 实时数据发送器 (send_signal_data.py)
- ✨ **新增**: 网络数据接收和解析功能
- ✨ **新增**: 频谱分析和星座图可视化
- ✨ **新增**: 信号类型自动识别
- 🔧 **修复**: matplotlib中文字体显示
- ✅ 所有测试通过

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

