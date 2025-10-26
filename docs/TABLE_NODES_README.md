# 表格数据节点使用指南

## 📊 概述

表格节点系统允许你在ComfyUI中加载、处理和显示表格数据（CSV、Excel、DataFrame等），**直接在前端显示为交互式表格**，而不是转换成图片。

## 🎯 功能特性

- ✅ **直接显示表格**：在前端以交互式表格形式展示
- ✅ **多种格式支持**：CSV、Excel、DataFrame、字典、列表
- ✅ **自动类型识别**：显示列的数据类型
- ✅ **大数据支持**：支持显示前N行（避免卡顿）
- ✅ **美观UI**：暗色主题，支持排序和筛选
- ✅ **点击查看**：在节点上点击即可打开表格弹窗

## 📦 节点列表

### 1. PreviewTable（预览表格）📊

在前端显示表格数据的输出节点。

**输入**：
- `table_data`：表格数据（必需）
- `max_rows`：最大显示行数（可选，默认100）
- `title`：表格标题（可选）

**输出**：无（输出节点）

**使用场景**：
- 查看数据分析结果
- 检查数据加载是否正确
- 展示处理后的数据

### 2. LoadCSV（加载CSV）📄

从CSV文件加载数据。

**输入**：
- `file_path`：CSV文件路径（必需）
- `encoding`：文件编码（可选，默认utf-8）
- `separator`：分隔符（可选，默认逗号）

**输出**：
- `table_data`：表格数据

**示例**：
```
file_path: examples/sample_data.csv
encoding: utf-8
separator: ,
```

### 3. LoadExcel（加载Excel）📊

从Excel文件加载数据。

**输入**：
- `file_path`：Excel文件路径（必需）
- `sheet_name`：工作表名称或索引（可选，默认0）

**输出**：
- `table_data`：表格数据

**示例**：
```
file_path: data/report.xlsx
sheet_name: 0  # 或 "Sheet1"
```

### 4. DataFrameToTable（转换为表格）🔄

将任意数据转换为表格格式。

**输入**：
- `data`：任意数据

**输出**：
- `table_data`：表格数据

**支持的数据类型**：
- DataFrame
- 字典：`{"col1": [1,2,3], "col2": [4,5,6]}`
- 列表的列表：`[[1,2], [3,4]]`
- 字典的列表：`[{"a":1}, {"a":2}]`
- NumPy数组

## 🚀 使用示例

### 示例1：加载并预览CSV

创建工作流：
```
LoadCSV → PreviewTable
```

配置：
- **LoadCSV**：
  - file_path: `examples/sample_data.csv`
- **PreviewTable**：
  - max_rows: `100`
  - title: `Employee Data`

运行后会在前端显示交互式表格！

### 示例2：加载Excel并显示

```
LoadExcel → PreviewTable
```

配置：
- **LoadExcel**：
  - file_path: `data.xlsx`
  - sheet_name: `0`
- **PreviewTable**：
  - title: `Excel Sheet Data`

### 示例3：处理信号数据后显示

```
NetworkReceiverNode → SignalAnalyzer → DataFrameToTable → PreviewTable
```

这样可以将信号分析结果转换为表格显示。

### 示例4：创建自定义数据表

在Python节点中：
```python
import pandas as pd

# 创建数据
data = pd.DataFrame({
    "Signal": ["QPSK", "QAM16", "FSK"],
    "SNR": [15.2, 18.5, 12.3],
    "BER": [0.001, 0.0005, 0.002]
})

return {"result": (data,)}
```

然后连接到 `PreviewTable` 显示。

## 🎨 前端显示特性

### 表格UI特性

- **暗色主题**：适配ComfyUI界面
- **固定表头**：滚动时表头保持可见
- **类型显示**：每列显示数据类型
- **行索引**：显示行号
- **交替行色**：提高可读性
- **数值格式化**：
  - 整数：直接显示
  - 浮点数：保留4位小数
  - 布尔值：绿色/红色标识
  - Null值：灰色显示

### 交互操作

1. **自动弹出**：节点执行后自动显示表格
2. **点击查看**：点击节点底部可重新打开表格
3. **关闭表格**：
   - 点击"关闭"按钮
   - 点击背景遮罩
   - 按ESC键

## 📁 文件结构

```
simple_comfyui/
├── table_nodes.py           # 后端节点定义
├── web_extensions/
│   └── tablePreview.js      # 前端显示组件
├── examples/
│   └── sample_data.csv      # 示例数据
└── docs/
    └── TABLE_NODES_README.md # 本文档
```

## 🔧 依赖要求

确保已安装pandas：

```bash
pip install pandas openpyxl
```

在 `requirements.txt` 中添加：
```
pandas>=1.5.0
openpyxl>=3.0.0  # 用于Excel支持
```

## 🐛 常见问题

### Q: 表格不显示？

1. 检查浏览器Console（F12）是否有错误
2. 确认 `web_extensions/tablePreview.js` 已加载
3. 刷新页面（Ctrl+Shift+R）

### Q: CSV加载失败？

1. 检查文件路径是否正确
2. 确认文件编码（中文可能需要gbk）
3. 检查分隔符是否正确

### Q: 数据显示不完整？

默认只显示前100行，可以调整 `max_rows` 参数。

### Q: 如何导出表格数据？

在PreviewTable节点执行后，数据会保存到 `temp/table_*.json`，可以读取该文件。

### Q: 支持哪些数据格式？

- CSV（推荐）
- Excel（.xlsx, .xls）
- Pandas DataFrame
- Python字典/列表
- NumPy数组

## 🎯 高级用法

### 1. 连接数据处理管道

```
LoadCSV → FilterData → TransformData → PreviewTable
```

### 2. 多表格对比

```
LoadCSV1 → PreviewTable1
LoadCSV2 → PreviewTable2
```

可以同时显示多个表格进行对比。

### 3. 与信号节点结合

```
NetworkReceiverNode → BufferNode → AnalyzeNode → DataFrameToTable → PreviewTable
```

将信号处理结果可视化为表格。

## 📊 性能建议

- **大数据**：设置合理的 `max_rows`（建议100-1000）
- **实时数据**：考虑采样或聚合后再显示
- **多列数据**：前端会自动添加横向滚动条

## 🔄 版本历史

### v1.0.0 (2025-10-26)
- ✅ 初始版本
- ✅ PreviewTable节点
- ✅ LoadCSV/LoadExcel节点
- ✅ DataFrameToTable节点
- ✅ 前端表格显示组件
- ✅ 暗色主题UI

## 💡 未来计划

- [ ] 表格排序功能
- [ ] 列筛选功能
- [ ] 导出CSV/Excel
- [ ] 数据统计摘要
- [ ] 图表可视化集成

---

**祝使用愉快！** 📊✨

