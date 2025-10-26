# 实时信号数据发送器

## 快速开始

### Windows
```bash
双击运行: send_signal_data.bat
```

### 命令行
```bash
python send_signal_data.py
```

## 使用流程

1. **启动ComfyUI服务器**
   ```bash
   python full_server.py
   ```

2. **在浏览器中创建工作流** (http://127.0.0.1:8188)
   ```
   NetworkReceiver (port=8888, continuous=true)
     ↓
   FrameParser → DataConverter → SpectrumAnalyzer → PreviewImage
   ```

3. **运行工作流** (点击 "Queue Prompt")

4. **启动数据发送器**
   - 选择 "1" - 快速启动（默认参数）
   - 或选择 "2" - 交互模式（自定义参数）

5. **观察ComfyUI中的实时显示**

## 参数说明

### 快速启动（默认参数）
- 信号类型: QPSK
- 目标地址: 127.0.0.1:8888
- 发送间隔: 1秒
- 样本数量: 1024
- 信噪比: 20 dB

### 交互模式
可自定义所有参数：
- **信号类型**: QPSK / QAM16 / FSK / ASK
- **目标地址**: 本地或远程IP
- **目标端口**: 自定义端口号
- **发送间隔**: 控制发送频率
- **样本数量**: 512 - 8192
- **信噪比**: 5 - 30 dB

## 停止发送

按 **Ctrl+C** 停止

## 输出示例

```
[14:23:45] Frame #0001 |   2072 bytes | Power: +0.5 dB | QPSK
[14:23:46] Frame #0002 |   2072 bytes | Power: +0.3 dB | QPSK
[14:23:47] Frame #0003 |   2072 bytes | Power: +0.6 dB | QPSK
```

## 编程调用

```python
from send_signal_data import send_data_continuously

send_data_continuously(
    host="127.0.0.1",
    port=8888,
    signal_type="QAM16",
    interval=0.5,
    num_samples=2048,
    snr_db=25
)
```

