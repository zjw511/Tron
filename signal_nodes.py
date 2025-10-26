"""
通信信号处理节点模块
包含网络数据接收、帧解析、信号处理和可视化节点
"""
from abc import ABC
from typing import Dict, List, Any, Optional
from nodes import NodeBase
import socket
import struct
import threading
import queue
import time
import numpy as np
from PIL import Image
import io
import os
from pathlib import Path

# 尝试导入matplotlib用于可视化
try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
    
    # 配置中文字体支持
    def setup_chinese_font():
        """配置matplotlib的中文字体支持（跨平台）"""
        import platform
        from matplotlib import font_manager
        
        # 候选字体列表（按优先级）
        font_candidates = []
        
        system = platform.system()
        if system == 'Windows':
            # Windows系统字体
            font_candidates = [
                'Microsoft YaHei',      # 微软雅黑
                'SimHei',               # 黑体
                'SimSun',               # 宋体
                'KaiTi',                # 楷体
                'FangSong'              # 仿宋
            ]
        elif system == 'Darwin':  # macOS
            font_candidates = [
                'PingFang SC',          # 苹方-简
                'STHeiti',              # 华文黑体
                'Heiti SC',             # 黑体-简
                'STSong',               # 华文宋体
            ]
        else:  # Linux
            font_candidates = [
                'WenQuanYi Micro Hei',  # 文泉驿微米黑
                'WenQuanYi Zen Hei',    # 文泉驿正黑
                'Droid Sans Fallback',  # Droid备用字体
                'Noto Sans CJK SC',     # 思源黑体
                'Noto Sans CJK TC',     # 思源黑体繁体
            ]
        
        # 获取系统中所有可用字体
        available_fonts = set(f.name for f in font_manager.fontManager.ttflist)
        
        # 查找第一个可用的中文字体
        selected_font = None
        for font in font_candidates:
            if font in available_fonts:
                selected_font = font
                break
        
        if selected_font:
            # 配置matplotlib使用找到的字体
            plt.rcParams['font.sans-serif'] = [selected_font]
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
            print(f"[OK] Configured matplotlib Chinese font: {selected_font}")
            return True
        else:
            # 如果没找到中文字体，尝试使用系统默认字体
            print("[Warning] No Chinese font found, using default font (Chinese may not display correctly)")
            plt.rcParams['axes.unicode_minus'] = False
            return False
    
    # 自动配置中文字体
    setup_chinese_font()
    
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[Warning] matplotlib not available, visualization nodes will be limited")


# =============================================================================
# 数据结构定义
# =============================================================================

class SignalFrame:
    """信号帧数据结构"""
    def __init__(self):
        self.frame_id = 0
        self.timestamp = 0.0
        self.frame_type = 0
        self.data_length = 0
        self.raw_data = b''
        self.parsed = False
        
    def __repr__(self):
        return f"SignalFrame(id={self.frame_id}, type={self.frame_type}, len={self.data_length})"


class SignalData:
    """转换后的信号数据"""
    def __init__(self):
        self.iq_data = None  # IQ数据 (复数数组)
        self.frequency = 0.0  # 中心频率
        self.sample_rate = 0.0  # 采样率
        self.power = 0.0  # 功率
        self.azimuth = 0.0  # 方位角
        self.elevation = 0.0  # 俯仰角
        self.signal_type = "UNKNOWN"  # 信号类型
        self.symbol_rate = 0.0  # 符号速率
        self.metadata = {}  # 其他元数据


# =============================================================================
# 1. 网络接收节点
# =============================================================================

class NetworkReceiverNode(NodeBase):
    """网络数据接收节点 - 从UDP/TCP端口接收数据"""
    
    # 类级别的接收器管理（防止重复创建）
    _active_receivers = {}  # key: "protocol:host:port", value: {"thread": thread, "queue": queue, "running": flag, "socket": socket}
    _receivers_lock = threading.Lock()
    
    def __init__(self):
        super().__init__()
        self.name = "NetworkReceiver"
        self.category = "signal/input"
        self.icon = "📡"
        self.inputs = []
        self.outputs = ["RAW_DATA"]
        self.description = "从网络端口接收原始数据流"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "protocol": [["UDP", "TCP"], {"default": "UDP"}],
                    "host": ["STRING", {"default": "0.0.0.0"}],
                    "port": ["INT", {"default": 8888, "min": 1024, "max": 65535}],
                    "buffer_size": ["INT", {"default": 65536, "min": 1024, "max": 65536}],
                    "queue_size": ["INT", {"default": 5000, "min": 10, "max": 10000}],
                    "continuous": ["BOOLEAN", {"default": True}],
                    "timeout": ["FLOAT", {"default": 1.0, "min": 0.1, "max": 60.0}]
                }
            },
            "output": ["RAW_DATA"],
            "output_is_list": [False],
            "output_name": ["RAW_DATA"],
            "name": "NetworkReceiver",
            "display_name": "网络接收器",
            "description": "从网络端口接收原始数据流",
            "category": "signal/input",
            "output_node": False
        }
    
    @staticmethod
    def _receive_loop(receiver_key, protocol, host, port, buffer_size, timeout):
        """接收数据循环（静态方法）"""
        receiver = NetworkReceiverNode._active_receivers.get(receiver_key)
        if not receiver:
            return
        
        sock_obj = None
        try:
            if protocol == "UDP":
                sock_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:
                sock_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            sock_obj.settimeout(timeout)
            sock_obj.bind((host, port))
            receiver["socket"] = sock_obj
            
            if protocol == "TCP":
                sock_obj.listen(1)
                print(f"    [OK] TCP server listening on {host}:{port}")
                conn, addr = sock_obj.accept()
                print(f"    [OK] TCP connection from {addr}")
                sock = conn
            else:
                print(f"    [OK] UDP receiver started on {host}:{port}")
                sock = sock_obj
            
            while receiver["running"]:
                try:
                    if protocol == "UDP":
                        data, addr = sock.recvfrom(buffer_size)
                    else:
                        data = sock.recv(buffer_size)
                    
                    if data:
                        timestamp = time.time()
                        data_queue = receiver["queue"]
                        if not data_queue.full():
                            data_queue.put((data, timestamp))
                        else:
                            # 队列满时丢弃最旧的数据
                            try:
                                data_queue.get_nowait()
                                data_queue.put((data, timestamp))
                            except queue.Empty:
                                pass
                    
                except socket.timeout:
                    continue
                except OSError as e:
                    # Windows错误10040: 缓冲区太小
                    if e.errno == 10040:
                        print(f"    [Error] Buffer too small! Received packet larger than {buffer_size} bytes")
                        print(f"    [Tip] Increase buffer_size parameter (current: {buffer_size}, max: 65536)")
                        continue  # 继续运行，不退出
                    elif receiver["running"]:
                        print(f"    [Error] Receive error: {e}")
                        break
                except Exception as e:
                    if receiver["running"]:
                        print(f"    [Error] Receive error: {e}")
                    break
        
        except Exception as e:
            print(f"    [Error] Network receiver error: {e}")
        finally:
            if sock_obj:
                try:
                    sock_obj.close()
                except:
                    pass
            # 清理接收器记录
            with NetworkReceiverNode._receivers_lock:
                if receiver_key in NetworkReceiverNode._active_receivers:
                    NetworkReceiverNode._active_receivers[receiver_key]["running"] = False
                    print(f"    [OK] Stopped receiver {receiver_key}")
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行网络接收"""
        protocol = inputs.get("protocol", "UDP")
        host = inputs.get("host", "0.0.0.0")
        port = inputs.get("port", 8888)
        buffer_size = inputs.get("buffer_size", 65536)  # 默认64KB，避免WinError 10040
        queue_size = inputs.get("queue_size", 5000)  # 队列大小，默认1000
        continuous = inputs.get("continuous", True)
        timeout = inputs.get("timeout", 1.0)
        
        # 生成接收器唯一标识
        receiver_key = f"{protocol}:{host}:{port}"
        
        if continuous:
            # 持续模式：使用类级别的接收器管理
            with self._receivers_lock:
                receiver = self._active_receivers.get(receiver_key)
                
                # 如果接收器不存在或已停止，创建新的
                if not receiver or not receiver["running"] or not receiver["thread"].is_alive():
                    # 清理旧接收器
                    if receiver:
                        receiver["running"] = False
                        if receiver.get("socket"):
                            try:
                                receiver["socket"].close()
                            except:
                                pass
                    
                    # 创建新接收器（使用用户指定的队列大小）
                    new_queue = queue.Queue(maxsize=queue_size)
                    receiver = {
                        "queue": new_queue,
                        "running": True,
                        "socket": None,
                        "thread": None
                    }
                    
                    thread = threading.Thread(
                        target=self._receive_loop,
                        args=(receiver_key, protocol, host, port, buffer_size, timeout),
                        daemon=True
                    )
                    receiver["thread"] = thread
                    self._active_receivers[receiver_key] = receiver
                    thread.start()
                    
                    print(f"    [OK] Started continuous {protocol} receiver on {host}:{port} (key: {receiver_key})")
                
                # 从接收器队列获取数据
                data_queue = receiver["queue"]
            
            # 获取数据（非阻塞）
            try:
                data, timestamp = data_queue.get_nowait()
                print(f"    [OK] Received {len(data)} bytes at {timestamp:.3f}")
                return {
                    "RAW_DATA": {
                        "data": data,
                        "timestamp": timestamp,
                        "length": len(data)
                    }
                }
            except queue.Empty:
                return {}
        
        else:
            # 非持续模式：单次接收
            try:
                if protocol == "UDP":
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                sock.settimeout(timeout)
                sock.bind((host, port))
                
                if protocol == "TCP":
                    sock.listen(1)
                    conn, addr = sock.accept()
                    data = conn.recv(buffer_size)
                    conn.close()
                else:
                    data, addr = sock.recvfrom(buffer_size)
                
                sock.close()
                timestamp = time.time()
                print(f"    [OK] Single receive: {len(data)} bytes")
                return {
                    "RAW_DATA": {
                        "data": data,
                        "timestamp": timestamp,
                        "length": len(data)
                    }
                }
            except OSError as e:
                if e.errno == 10040:
                    print(f"    [Error] Buffer too small! Received packet larger than {buffer_size} bytes")
                    print(f"    [Tip] Increase buffer_size parameter (current: {buffer_size}, max: 65536)")
                else:
                    print(f"    [X] Single receive failed: {e}")
                return {}
            except Exception as e:
                print(f"    [X] Single receive failed: {e}")
                return {}
    
    @classmethod
    def stop_all_receivers(cls):
        """停止所有活动的接收器"""
        with cls._receivers_lock:
            for receiver_key, receiver in list(cls._active_receivers.items()):
                receiver["running"] = False
                if receiver.get("socket"):
                    try:
                        receiver["socket"].close()
                    except:
                        pass
                print(f"    [OK] Stopping receiver {receiver_key}")
            cls._active_receivers.clear()


# =============================================================================
# 2. 帧解析节点
# =============================================================================

class FrameParserNode(NodeBase):
    """帧结构解析节点 - 解析网络数据的帧结构"""
    
    def __init__(self):
        super().__init__()
        self.name = "FrameParser"
        self.category = "signal/processing"
        self.icon = "🔍"
        self.inputs = ["RAW_DATA"]
        self.outputs = ["FRAME"]
        self.description = "解析网络数据的帧结构"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "raw_data": ["RAW_DATA", {}],
                    "frame_header": ["STRING", {"default": "0xAA55"}],
                    "header_size": ["INT", {"default": 16, "min": 4, "max": 1024}],
                    "byte_order": [["little", "big"], {"default": "little"}]
                }
            },
            "output": ["FRAME"],
            "output_is_list": [False],
            "output_name": ["FRAME"],
            "name": "FrameParser",
            "display_name": "帧解析器",
            "description": "解析网络数据的帧结构",
            "category": "signal/processing",
            "output_node": False
        }
    
    def _parse_frame(self, data: bytes, header_bytes: bytes, header_size: int, byte_order: str) -> SignalFrame:
        """解析单个帧"""
        frame = SignalFrame()
        
        # 查找帧头
        header_pos = data.find(header_bytes)
        if header_pos == -1:
            print(f"    [Warning] Frame header not found")
            return frame
        
        # 提取帧头信息（假设标准帧结构）
        try:
            header_data = data[header_pos:header_pos + header_size]
            if len(header_data) < header_size:
                print(f"    [Warning] Incomplete frame header")
                return frame
            
            endian = '<' if byte_order == 'little' else '>'
            
            # 解析帧头 (示例格式：2字节帧头 + 4字节ID + 8字节时间戳 + 2字节类型)
            offset = len(header_bytes)
            
            if header_size >= offset + 4:
                frame.frame_id = struct.unpack(f'{endian}I', header_data[offset:offset+4])[0]
                offset += 4
            
            if header_size >= offset + 8:
                frame.timestamp = struct.unpack(f'{endian}d', header_data[offset:offset+8])[0]
                offset += 8
            
            if header_size >= offset + 2:
                frame.frame_type = struct.unpack(f'{endian}H', header_data[offset:offset+2])[0]
                offset += 2
            
            # 数据长度（剩余数据）
            frame.data_length = len(data) - header_pos - header_size
            frame.raw_data = data[header_pos + header_size:]
            frame.parsed = True
            
        except Exception as e:
            print(f"    [Error] Frame parsing error: {e}")
        
        return frame
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行帧解析"""
        raw_data_dict = inputs.get("raw_data", {})
        frame_header_str = inputs.get("frame_header", "0xAA55")
        header_size = inputs.get("header_size", 16)
        byte_order = inputs.get("byte_order", "little")
        
        if not raw_data_dict or "data" not in raw_data_dict:
            print(f"    [X] No raw data to parse")
            return {}
        
        data = raw_data_dict["data"]
        
        # 解析帧头字符串
        try:
            if frame_header_str.startswith("0x"):
                header_bytes = bytes.fromhex(frame_header_str[2:])
            else:
                header_bytes = frame_header_str.encode()
        except Exception as e:
            print(f"    [Error] Invalid frame header: {e}")
            return {}
        
        # 解析帧
        frame = self._parse_frame(data, header_bytes, header_size, byte_order)
        
        if frame.parsed:
            print(f"    [OK] Parsed frame: ID={frame.frame_id}, Type={frame.frame_type}, Len={frame.data_length}")
            return {"FRAME": frame}
        else:
            print(f"    [X] Frame parsing failed")
            return {}


# =============================================================================
# 3. 数据转换节点
# =============================================================================

class DataConverterNode(NodeBase):
    """数据格式转换节点 - 将帧数据转换为信号数据"""
    
    def __init__(self):
        super().__init__()
        self.name = "DataConverter"
        self.category = "signal/processing"
        self.icon = "🔄"
        self.inputs = ["FRAME"]
        self.outputs = ["SIGNAL_DATA"]
        self.description = "将帧数据转换为信号数据格式"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "frame": ["FRAME", {}],
                    "data_format": [["IQ_INT16", "IQ_FLOAT32", "IQ_COMPLEX64", "POWER_SPECTRUM"], 
                                   {"default": "IQ_INT16"}],
                    "sample_rate": ["FLOAT", {"default": 2.4e6, "min": 1e3, "max": 100e6}],
                    "center_frequency": ["FLOAT", {"default": 1.575e9, "min": 1e6, "max": 10e9}]
                }
            },
            "output": ["SIGNAL_DATA"],
            "output_is_list": [False],
            "output_name": ["SIGNAL_DATA"],
            "name": "DataConverter",
            "display_name": "数据转换器",
            "description": "将帧数据转换为信号数据格式",
            "category": "signal/processing",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行数据转换"""
        frame = inputs.get("frame")
        data_format = inputs.get("data_format", "IQ_INT16")
        sample_rate = inputs.get("sample_rate", 2.4e6)
        center_frequency = inputs.get("center_frequency", 1.575e9)
        
        if not frame or not hasattr(frame, 'raw_data'):
            print(f"    [X] No frame data to convert")
            return {}
        
        signal_data = SignalData()
        signal_data.sample_rate = sample_rate
        signal_data.frequency = center_frequency
        
        try:
            raw_data = frame.raw_data
            
            # 根据格式转换数据
            if data_format == "IQ_INT16":
                # 16位整数IQ数据
                samples = len(raw_data) // 4  # 每个IQ样本4字节(I:2, Q:2)
                iq_array = np.frombuffer(raw_data[:samples*4], dtype=np.int16)
                i_samples = iq_array[0::2].astype(np.float32) / 32768.0
                q_samples = iq_array[1::2].astype(np.float32) / 32768.0
                signal_data.iq_data = i_samples + 1j * q_samples
                
            elif data_format == "IQ_FLOAT32":
                # 32位浮点IQ数据
                samples = len(raw_data) // 8  # 每个IQ样本8字节
                iq_array = np.frombuffer(raw_data[:samples*8], dtype=np.float32)
                signal_data.iq_data = iq_array[0::2] + 1j * iq_array[1::2]
                
            elif data_format == "IQ_COMPLEX64":
                # 64位复数数据
                signal_data.iq_data = np.frombuffer(raw_data, dtype=np.complex64)
                
            elif data_format == "POWER_SPECTRUM":
                # 功率谱数据（实数）
                power_data = np.frombuffer(raw_data, dtype=np.float32)
                signal_data.iq_data = power_data
            
            # 计算功率
            if signal_data.iq_data is not None:
                signal_data.power = float(np.mean(np.abs(signal_data.iq_data)**2))
                
                print(f"    [OK] Converted {len(signal_data.iq_data)} samples, Power={signal_data.power:.2e}")
                return {"SIGNAL_DATA": signal_data}
            else:
                print(f"    [X] Conversion failed")
                return {}
                
        except Exception as e:
            print(f"    [Error] Data conversion error: {e}")
            return {}


# =============================================================================
# 4. 频谱分析节点
# =============================================================================

class SpectrumAnalyzerNode(NodeBase):
    """频谱分析节点 - 生成信号的频谱图"""
    
    def __init__(self):
        super().__init__()
        self.name = "SpectrumAnalyzer"
        self.category = "signal/visualization"
        self.icon = "📊"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["IMAGE"]
        self.description = "生成信号频谱图"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "fft_size": ["INT", {"default": 1024, "min": 64, "max": 16384}],
                    "window": [["hanning", "hamming", "blackman", "rectangular"], {"default": "hanning"}],
                    "log_scale": ["BOOLEAN", {"default": True}],
                    "width": ["INT", {"default": 800, "min": 400, "max": 2048}],
                    "height": ["INT", {"default": 600, "min": 300, "max": 1536}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "SpectrumAnalyzer",
            "display_name": "频谱分析仪",
            "description": "生成信号频谱图",
            "category": "signal/visualization",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行频谱分析"""
        if not MATPLOTLIB_AVAILABLE:
            print(f"    [X] matplotlib not available")
            return {}
        
        signal_data = inputs.get("signal_data")
        fft_size = inputs.get("fft_size", 1024)
        window_type = inputs.get("window", "hanning")
        log_scale = inputs.get("log_scale", True)
        width = inputs.get("width", 800)
        height = inputs.get("height", 600)
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for spectrum analysis")
            return {}
        
        try:
            iq_data = signal_data.iq_data
            
            # 应用窗函数
            if window_type == "hanning":
                window = np.hanning(min(fft_size, len(iq_data)))
            elif window_type == "hamming":
                window = np.hamming(min(fft_size, len(iq_data)))
            elif window_type == "blackman":
                window = np.blackman(min(fft_size, len(iq_data)))
            else:
                window = np.ones(min(fft_size, len(iq_data)))
            
            # 计算FFT
            if len(iq_data) >= fft_size:
                windowed_data = iq_data[:fft_size] * window
            else:
                windowed_data = iq_data * window[:len(iq_data)]
                windowed_data = np.pad(windowed_data, (0, fft_size - len(iq_data)), 'constant')
            
            fft_result = np.fft.fftshift(np.fft.fft(windowed_data))
            power_spectrum = np.abs(fft_result) ** 2
            
            if log_scale:
                power_spectrum_db = 10 * np.log10(power_spectrum + 1e-10)
            else:
                power_spectrum_db = power_spectrum
            
            # 频率轴
            freq_axis = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/signal_data.sample_rate))
            freq_mhz = (signal_data.frequency + freq_axis) / 1e6
            
            # 绘图
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            ax.plot(freq_mhz, power_spectrum_db, linewidth=1)
            ax.set_xlabel('频率 (MHz)')
            ax.set_ylabel('功率 (dB)' if log_scale else '功率')
            ax.set_title(f'频谱图 - 中心频率: {signal_data.frequency/1e6:.2f} MHz')
            ax.grid(True, alpha=0.3)
            
            # 转换为PIL Image
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            image = Image.open(buf).copy()
            buf.close()
            plt.close(fig)
            
            print(f"    [OK] Generated spectrum plot: {image.size}")
            return {"IMAGE": image}
            
        except Exception as e:
            print(f"    [Error] Spectrum analysis error: {e}")
            return {}


# =============================================================================
# 5. 方位角处理节点
# =============================================================================

class AzimuthProcessorNode(NodeBase):
    """方位角处理节点 - 计算和显示信号方位角"""
    
    def __init__(self):
        super().__init__()
        self.name = "AzimuthProcessor"
        self.category = "signal/processing"
        self.icon = "🧭"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["SIGNAL_DATA", "IMAGE"]
        self.description = "计算信号方位角并生成可视化"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "algorithm": [["MUSIC", "ESPRIT", "PHASE_DIFF"], {"default": "PHASE_DIFF"}],
                    "num_elements": ["INT", {"default": 4, "min": 2, "max": 16}],
                    "element_spacing": ["FLOAT", {"default": 0.5, "min": 0.1, "max": 2.0}]
                }
            },
            "output": ["SIGNAL_DATA", "IMAGE"],
            "output_is_list": [False, False],
            "output_name": ["SIGNAL_DATA", "IMAGE"],
            "name": "AzimuthProcessor",
            "display_name": "方位角处理器",
            "description": "计算信号方位角并生成可视化",
            "category": "signal/processing",
            "output_node": False
        }
    
    def _estimate_azimuth_simple(self, iq_data: np.ndarray, num_elements: int) -> float:
        """简单的方位角估计（基于相位差）"""
        # 模拟多天线阵列接收
        # 这里使用简化算法，实际应用需要更复杂的DOA算法
        
        # 计算平均相位
        phase = np.angle(np.mean(iq_data))
        
        # 转换为方位角（0-360度）
        azimuth = (phase / np.pi * 180) % 360
        
        return azimuth
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行方位角处理"""
        signal_data = inputs.get("signal_data")
        algorithm = inputs.get("algorithm", "PHASE_DIFF")
        num_elements = inputs.get("num_elements", 4)
        element_spacing = inputs.get("element_spacing", 0.5)
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for azimuth processing")
            return {}
        
        try:
            # 计算方位角
            azimuth = self._estimate_azimuth_simple(signal_data.iq_data, num_elements)
            signal_data.azimuth = azimuth
            
            # 生成方位角可视化
            if MATPLOTLIB_AVAILABLE:
                fig = plt.figure(figsize=(6, 6))
                ax = fig.add_subplot(111, projection='polar')
                
                # 绘制方位角指示
                theta = np.radians(azimuth)
                ax.arrow(0, 0, theta, 0.8, head_width=0.1, head_length=0.1, 
                        fc='red', ec='red', linewidth=2)
                
                ax.set_theta_zero_location('N')
                ax.set_theta_direction(-1)
                ax.set_title(f'方位角: {azimuth:.1f}°', pad=20)
                
                # 转换为PIL Image
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                image = Image.open(buf).copy()
                buf.close()
                plt.close(fig)
                
                print(f"    [OK] Azimuth calculated: {azimuth:.2f}°")
                return {"SIGNAL_DATA": signal_data, "IMAGE": image}
            else:
                print(f"    [OK] Azimuth calculated: {azimuth:.2f}° (no visualization)")
                return {"SIGNAL_DATA": signal_data}
                
        except Exception as e:
            print(f"    [Error] Azimuth processing error: {e}")
            return {}


# =============================================================================
# 6. 信号类型识别节点
# =============================================================================

class SignalClassifierNode(NodeBase):
    """信号类型识别节点 - 识别信号调制类型"""
    
    def __init__(self):
        super().__init__()
        self.name = "SignalClassifier"
        self.category = "signal/processing"
        self.icon = "🎯"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["SIGNAL_DATA"]
        self.description = "识别信号的调制类型"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "method": [["FEATURE_BASED", "ML_BASED", "STATISTICAL"], {"default": "FEATURE_BASED"}]
                }
            },
            "output": ["SIGNAL_DATA"],
            "output_is_list": [False],
            "output_name": ["SIGNAL_DATA"],
            "name": "SignalClassifier",
            "display_name": "信号分类器",
            "description": "识别信号的调制类型",
            "category": "signal/processing",
            "output_node": False
        }
    
    def _classify_signal(self, iq_data: np.ndarray) -> str:
        """简单的信号分类（基于特征）"""
        # 计算信号特征
        amplitude = np.abs(iq_data)
        phase = np.angle(iq_data)
        
        # 振幅变化
        amp_std = np.std(amplitude)
        amp_mean = np.mean(amplitude)
        amp_variation = amp_std / (amp_mean + 1e-10)
        
        # 相位变化
        phase_diff = np.diff(phase)
        phase_std = np.std(phase_diff)
        
        # 简单分类规则
        if amp_variation < 0.1 and phase_std > 0.5:
            signal_type = "PSK"  # 相移键控
        elif amp_variation > 0.3 and phase_std < 0.3:
            signal_type = "ASK"  # 振幅键控
        elif amp_variation > 0.2 and phase_std > 0.3:
            signal_type = "QAM"  # 正交振幅调制
        elif amp_variation < 0.15 and phase_std > 1.0:
            signal_type = "FSK"  # 频移键控
        else:
            signal_type = "UNKNOWN"
        
        return signal_type
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行信号分类"""
        signal_data = inputs.get("signal_data")
        method = inputs.get("method", "FEATURE_BASED")
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for classification")
            return {}
        
        try:
            signal_type = self._classify_signal(signal_data.iq_data)
            signal_data.signal_type = signal_type
            
            print(f"    [OK] Signal classified as: {signal_type}")
            return {"SIGNAL_DATA": signal_data}
            
        except Exception as e:
            print(f"    [Error] Signal classification error: {e}")
            return {}


# =============================================================================
# 7. 频点检测节点
# =============================================================================

class FrequencyDetectorNode(NodeBase):
    """频点检测节点 - 检测信号中的主要频率分量"""
    
    def __init__(self):
        super().__init__()
        self.name = "FrequencyDetector"
        self.category = "signal/processing"
        self.icon = "📶"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["SIGNAL_DATA", "IMAGE"]
        self.description = "检测信号中的主要频率分量"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "num_peaks": ["INT", {"default": 5, "min": 1, "max": 20}],
                    "threshold_db": ["FLOAT", {"default": -40.0, "min": -80.0, "max": 0.0}]
                }
            },
            "output": ["SIGNAL_DATA", "IMAGE"],
            "output_is_list": [False, False],
            "output_name": ["SIGNAL_DATA", "IMAGE"],
            "name": "FrequencyDetector",
            "display_name": "频点检测器",
            "description": "检测信号中的主要频率分量",
            "category": "signal/processing",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行频点检测"""
        signal_data = inputs.get("signal_data")
        num_peaks = inputs.get("num_peaks", 5)
        threshold_db = inputs.get("threshold_db", -40.0)
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for frequency detection")
            return {}
        
        try:
            iq_data = signal_data.iq_data
            
            # FFT分析
            fft_size = min(2048, len(iq_data))
            fft_result = np.fft.fftshift(np.fft.fft(iq_data[:fft_size]))
            power_spectrum = np.abs(fft_result) ** 2
            power_db = 10 * np.log10(power_spectrum + 1e-10)
            
            # 检测峰值
            from scipy import signal as scipy_signal
            peaks, properties = scipy_signal.find_peaks(power_db, height=threshold_db, distance=10)
            
            # 选择最强的峰值
            if len(peaks) > num_peaks:
                peak_heights = properties['peak_heights']
                top_indices = np.argsort(peak_heights)[-num_peaks:]
                peaks = peaks[top_indices]
            
            # 转换为频率
            freq_axis = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/signal_data.sample_rate))
            detected_freqs = signal_data.frequency + freq_axis[peaks]
            
            # 存储检测结果
            signal_data.metadata['detected_frequencies'] = detected_freqs.tolist()
            
            # 生成可视化
            if MATPLOTLIB_AVAILABLE:
                fig, ax = plt.subplots(figsize=(10, 6))
                freq_mhz = (signal_data.frequency + freq_axis) / 1e6
                ax.plot(freq_mhz, power_db, linewidth=1)
                ax.plot(freq_mhz[peaks], power_db[peaks], 'rx', markersize=10, label='检测到的频点')
                ax.axhline(y=threshold_db, color='r', linestyle='--', alpha=0.5, label='阈值')
                ax.set_xlabel('频率 (MHz)')
                ax.set_ylabel('功率 (dB)')
                ax.set_title(f'频点检测 - 检测到 {len(peaks)} 个频点')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                # 转换为PIL Image
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                image = Image.open(buf).copy()
                buf.close()
                plt.close(fig)
                
                print(f"    [OK] Detected {len(peaks)} frequency peaks")
                return {"SIGNAL_DATA": signal_data, "IMAGE": image}
            else:
                print(f"    [OK] Detected {len(peaks)} frequency peaks (no visualization)")
                return {"SIGNAL_DATA": signal_data}
                
        except Exception as e:
            print(f"    [Error] Frequency detection error: {e}")
            return {}


# =============================================================================
# 8. 符号速率分析节点
# =============================================================================

class SymbolRateAnalyzerNode(NodeBase):
    """符号速率分析节点 - 估计信号的符号速率"""
    
    def __init__(self):
        super().__init__()
        self.name = "SymbolRateAnalyzer"
        self.category = "signal/processing"
        self.icon = "⏱️"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["SIGNAL_DATA"]
        self.description = "估计信号的符号速率"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "method": [["AUTOCORR", "CYCLIC", "FFT"], {"default": "AUTOCORR"}]
                }
            },
            "output": ["SIGNAL_DATA"],
            "output_is_list": [False],
            "output_name": ["SIGNAL_DATA"],
            "name": "SymbolRateAnalyzer",
            "display_name": "符号速率分析器",
            "description": "估计信号的符号速率",
            "category": "signal/processing",
            "output_node": False
        }
    
    def _estimate_symbol_rate(self, iq_data: np.ndarray, sample_rate: float) -> float:
        """估计符号速率（基于自相关）"""
        try:
            from scipy import signal as scipy_signal
        except ImportError:
            # 如果scipy不可用，返回默认估计
            return sample_rate / 10.0
        
        # 计算包络
        envelope = np.abs(iq_data)
        
        # 去除直流分量
        envelope = envelope - np.mean(envelope)
        
        # 计算自相关
        autocorr = np.correlate(envelope, envelope, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # 归一化
        autocorr = autocorr / autocorr[0]
        
        # 查找第一个显著峰值（排除0点）
        peaks, _ = scipy_signal.find_peaks(autocorr[1:], height=0.3)
        
        if len(peaks) > 0:
            # 第一个峰值对应符号周期
            symbol_period_samples = peaks[0] + 1
            symbol_rate = sample_rate / symbol_period_samples
        else:
            # 如果没有找到峰值，返回估计值
            symbol_rate = sample_rate / 10.0
        
        return symbol_rate
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行符号速率分析"""
        signal_data = inputs.get("signal_data")
        method = inputs.get("method", "AUTOCORR")
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for symbol rate analysis")
            return {}
        
        try:
            symbol_rate = self._estimate_symbol_rate(signal_data.iq_data, signal_data.sample_rate)
            signal_data.symbol_rate = symbol_rate
            
            print(f"    [OK] Estimated symbol rate: {symbol_rate/1e3:.2f} kSps")
            return {"SIGNAL_DATA": signal_data}
            
        except Exception as e:
            print(f"    [Error] Symbol rate analysis error: {e}")
            return {}


# =============================================================================
# 9. 星座图节点
# =============================================================================

class ConstellationDiagramNode(NodeBase):
    """星座图节点 - 生成IQ数据的星座图"""
    
    def __init__(self):
        super().__init__()
        self.name = "ConstellationDiagram"
        self.category = "signal/visualization"
        self.icon = "⭐"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["IMAGE"]
        self.description = "生成信号的星座图"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "max_points": ["INT", {"default": 10000, "min": 100, "max": 100000}],
                    "normalize": ["BOOLEAN", {"default": True}],
                    "show_density": ["BOOLEAN", {"default": True}],
                    "width": ["INT", {"default": 800, "min": 400, "max": 2048}],
                    "height": ["INT", {"default": 800, "min": 400, "max": 2048}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "ConstellationDiagram",
            "display_name": "星座图",
            "description": "生成信号的星座图",
            "category": "signal/visualization",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行星座图生成"""
        if not MATPLOTLIB_AVAILABLE:
            print(f"    [X] matplotlib not available")
            return {}
        
        signal_data = inputs.get("signal_data")
        max_points = inputs.get("max_points", 10000)
        normalize = inputs.get("normalize", True)
        show_density = inputs.get("show_density", True)
        width = inputs.get("width", 800)
        height = inputs.get("height", 800)
        
        if not signal_data or signal_data.iq_data is None:
            print(f"    [X] No signal data for constellation diagram")
            return {}
        
        try:
            iq_data = signal_data.iq_data
            
            # 限制点数
            if len(iq_data) > max_points:
                step = len(iq_data) // max_points
                iq_data = iq_data[::step]
            
            # 归一化
            if normalize:
                iq_data = iq_data / (np.max(np.abs(iq_data)) + 1e-10)
            
            # 提取I和Q
            i_data = np.real(iq_data)
            q_data = np.imag(iq_data)
            
            # 绘制星座图
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            
            if show_density:
                # 使用密度图
                ax.hexbin(i_data, q_data, gridsize=50, cmap='plasma', mincnt=1)
                ax.set_facecolor('black')
            else:
                # 使用散点图
                ax.scatter(i_data, q_data, s=1, alpha=0.5, c='cyan')
                ax.set_facecolor('black')
            
            ax.set_xlabel('I (同相)')
            ax.set_ylabel('Q (正交)')
            ax.set_title(f'星座图 - {signal_data.signal_type}')
            ax.grid(True, alpha=0.3, color='white')
            ax.axhline(y=0, color='w', linestyle='--', linewidth=0.5)
            ax.axvline(x=0, color='w', linestyle='--', linewidth=0.5)
            ax.set_aspect('equal')
            
            # 转换为PIL Image
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', facecolor='black')
            buf.seek(0)
            image = Image.open(buf).copy()
            buf.close()
            plt.close(fig)
            
            print(f"    [OK] Generated constellation diagram: {image.size}")
            return {"IMAGE": image}
            
        except Exception as e:
            print(f"    [Error] Constellation diagram error: {e}")
            return {}


# =============================================================================
# 10. 信号监视器节点 (输出节点)
# =============================================================================

class SignalMonitorNode(NodeBase):
    """信号监视器节点 - 显示信号的综合信息"""
    
    def __init__(self):
        super().__init__()
        self.name = "SignalMonitor"
        self.category = "signal/output"
        self.icon = "📺"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = []
        self.description = "显示信号的综合信息"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}]
                }
            },
            "output": [],
            "output_is_list": [],
            "output_name": [],
            "name": "SignalMonitor",
            "display_name": "信号监视器",
            "description": "显示信号的综合信息",
            "category": "signal/output",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行信号监视"""
        signal_data = inputs.get("signal_data")
        
        if not signal_data:
            print(f"    [X] No signal data to monitor")
            return {}
        
        print(f"\n    ═══════════════════════════════════════")
        print(f"    📺 信号监视器")
        print(f"    ═══════════════════════════════════════")
        print(f"    中心频率:   {signal_data.frequency/1e6:.3f} MHz")
        print(f"    采样率:     {signal_data.sample_rate/1e6:.3f} MSps")
        print(f"    信号功率:   {10*np.log10(signal_data.power+1e-10):.2f} dB")
        print(f"    信号类型:   {signal_data.signal_type}")
        print(f"    符号速率:   {signal_data.symbol_rate/1e3:.2f} kSps")
        print(f"    方位角:     {signal_data.azimuth:.1f}°")
        print(f"    俯仰角:     {signal_data.elevation:.1f}°")
        
        if signal_data.iq_data is not None:
            print(f"    样本数:     {len(signal_data.iq_data)}")
        
        if signal_data.metadata:
            print(f"    其他信息:   {len(signal_data.metadata)} 项")
            for key, value in signal_data.metadata.items():
                if isinstance(value, list) and len(value) > 3:
                    print(f"      - {key}: {len(value)} 个元素")
                else:
                    print(f"      - {key}: {value}")
        
        print(f"    ═══════════════════════════════════════\n")
        
        return {"status": "monitored"}


# =============================================================================
# 10.5. 信号信息可视化节点 (浏览器版 SignalMonitor)
# =============================================================================

class SignalInfoImageNode(NodeBase):
    """信号信息图像节点 - 生成信号信息图像供浏览器显示"""
    
    def __init__(self):
        super().__init__()
        self.name = "SignalInfoImage"
        self.category = "signal/visualization"
        self.icon = "📋"
        self.inputs = ["SIGNAL_DATA"]
        self.outputs = ["IMAGE"]
        self.description = "生成包含信号信息的图像，在浏览器中显示"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "signal_data": ["SIGNAL_DATA", {}],
                    "theme": [["light", "dark"], {"default": "dark"}],
                    "font_size": ["INT", {"default": 14, "min": 10, "max": 24}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "SignalInfoImage",
            "display_name": "信号信息面板",
            "description": "生成包含信号信息的图像，在浏览器中显示",
            "category": "signal/visualization",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """生成信号信息图像"""
        signal_data = inputs.get("signal_data")
        theme = inputs.get("theme", "dark")
        font_size = inputs.get("font_size", 14)
        
        if not signal_data:
            print(f"    [X] No signal data for info image")
            return {}
        
        if not MATPLOTLIB_AVAILABLE:
            print(f"    [X] matplotlib not available for info image")
            return {}
        
        try:
            # 设置主题颜色
            if theme == "dark":
                bg_color = '#1e1e1e'
                text_color = '#ffffff'
                header_color = '#4a9eff'
                border_color = '#3a3a3a'
                value_color = '#a0e0ff'
            else:
                bg_color = '#ffffff'
                text_color = '#000000'
                header_color = '#0066cc'
                border_color = '#cccccc'
                value_color = '#0099ff'
            
            # 创建图形
            fig = plt.figure(figsize=(10, 8), facecolor=bg_color)
            ax = fig.add_subplot(111)
            ax.set_facecolor(bg_color)
            ax.axis('off')
            
            # 准备信息文本
            info_lines = []
            
            # 标题
            info_lines.append(("📡 信号信息监视面板", header_color, font_size + 4, 'bold'))
            info_lines.append(("=" * 50, border_color, font_size - 2, 'normal'))
            info_lines.append(("", text_color, font_size, 'normal'))  # 空行
            
            # 基本信息
            info_lines.append(("🔷 基本参数", header_color, font_size + 2, 'bold'))
            info_lines.append(("", text_color, font_size, 'normal'))
            
            info_lines.append((f"  中心频率:  {signal_data.frequency/1e6:.3f} MHz", 
                             text_color, font_size, 'normal'))
            info_lines.append((f"  采样率:    {signal_data.sample_rate/1e6:.3f} MSps", 
                             text_color, font_size, 'normal'))
            info_lines.append((f"  信号功率:  {10*np.log10(signal_data.power+1e-10):.2f} dB", 
                             value_color, font_size, 'normal'))
            
            if signal_data.iq_data is not None:
                info_lines.append((f"  样本数:    {len(signal_data.iq_data)}", 
                                 text_color, font_size, 'normal'))
            
            # 空行
            info_lines.append(("", text_color, font_size, 'normal'))
            
            # 信号特征
            info_lines.append(("🔷 信号特征", header_color, font_size + 2, 'bold'))
            info_lines.append(("", text_color, font_size, 'normal'))
            
            info_lines.append((f"  信号类型:  {signal_data.signal_type}", 
                             value_color, font_size + 2, 'bold'))
            info_lines.append((f"  符号速率:  {signal_data.symbol_rate/1e3:.2f} kSps", 
                             text_color, font_size, 'normal'))
            
            # 空行
            info_lines.append(("", text_color, font_size, 'normal'))
            
            # 空间信息
            info_lines.append(("🔷 空间信息", header_color, font_size + 2, 'bold'))
            info_lines.append(("", text_color, font_size, 'normal'))
            
            info_lines.append((f"  方位角:    {signal_data.azimuth:.1f}°", 
                             text_color, font_size, 'normal'))
            info_lines.append((f"  俯仰角:    {signal_data.elevation:.1f}°", 
                             text_color, font_size, 'normal'))
            
            # 元数据（如果有）
            if signal_data.metadata:
                info_lines.append(("", text_color, font_size, 'normal'))
                info_lines.append(("🔷 其他信息", header_color, font_size + 2, 'bold'))
                info_lines.append(("", text_color, font_size, 'normal'))
                
                for key, value in signal_data.metadata.items():
                    if isinstance(value, list) and len(value) > 3:
                        info_lines.append((f"  {key}: {len(value)} 个元素", 
                                         text_color, font_size - 2, 'normal'))
                    elif isinstance(value, (int, float, str)) and len(str(value)) < 50:
                        info_lines.append((f"  {key}: {value}", 
                                         text_color, font_size - 2, 'normal'))
            
            # 底部信息
            info_lines.append(("", text_color, font_size, 'normal'))
            info_lines.append(("=" * 50, border_color, font_size - 2, 'normal'))
            info_lines.append((f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", 
                             border_color, font_size - 2, 'italic'))
            
            # 渲染文本
            y_pos = 0.95
            for text, color, size, weight in info_lines:
                # 处理字体样式（不指定fontfamily，使用全局配置的中文字体）
                text_kwargs = {
                    'fontsize': size,
                    'color': color,
                    'verticalalignment': 'top',
                    'transform': ax.transAxes
                }
                
                # 根据weight设置字体样式
                if weight == 'italic':
                    text_kwargs['fontstyle'] = 'italic'
                elif weight in ['bold', 'normal']:
                    text_kwargs['fontweight'] = weight
                
                ax.text(0.05, y_pos, text, **text_kwargs)
                # 根据字体大小调整行距
                y_pos -= (size / 300)
            
            # 保存为图像（使用内存缓冲区）
            from io import BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                       facecolor=bg_color, edgecolor='none')
            buf.seek(0)
            
            # 转换为PIL Image对象
            from PIL import Image
            image = Image.open(buf).copy()
            buf.close()
            plt.close(fig)
            
            print(f"    [OK] Generated signal info image: {image.size}")
            
            return {"IMAGE": image}
            
        except Exception as e:
            print(f"    [Error] Signal info image error: {e}")
            import traceback
            traceback.print_exc()
            return {}


# =============================================================================
# 11. 数据保存节点
# =============================================================================

class DataBufferNode(NodeBase):
    """数据缓冲节点 - 缓存数据并管理数据流"""
    
    # 类级别的缓冲区管理
    _buffers = {}  # key: buffer_id, value: {"queue": queue, "stats": stats_dict}
    _buffers_lock = threading.Lock()
    
    def __init__(self):
        super().__init__()
        self.name = "DataBuffer"
        self.category = "signal/processing"
        self.icon = "📦"
        self.inputs = ["RAW_DATA"]
        self.outputs = ["RAW_DATA", "BUFFER_STATS"]
        self.description = "缓存数据流，管理数据队列"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "raw_data": ["RAW_DATA", {}],
                    "buffer_id": ["STRING", {"default": "buffer_1"}],
                    "max_size": ["INT", {"default": 100, "min": 1, "max": 1000}],
                    "mode": [["queue", "stack", "overwrite"], {"default": "queue"}]
                }
            },
            "output": ["RAW_DATA", "BUFFER_STATS"],
            "output_is_list": [False, False],
            "output_name": ["RAW_DATA", "BUFFER_STATS"],
            "name": "DataBuffer",
            "display_name": "数据缓冲器",
            "description": "缓存数据流，管理数据队列",
            "category": "signal/processing",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行数据缓冲"""
        raw_data_dict = inputs.get("raw_data", {})
        buffer_id = inputs.get("buffer_id", "buffer_1")
        max_size = inputs.get("max_size", 100)
        mode = inputs.get("mode", "queue")
        
        with self._buffers_lock:
            # 初始化缓冲区
            if buffer_id not in self._buffers:
                self._buffers[buffer_id] = {
                    "queue": queue.Queue(maxsize=max_size),
                    "stats": {
                        "received_count": 0,
                        "received_bytes": 0,
                        "sent_count": 0,
                        "sent_bytes": 0,
                        "dropped_count": 0,
                        "dropped_bytes": 0,
                        "current_size": 0,
                        "max_size": max_size,
                        "mode": mode,
                        "last_update": time.time()
                    }
                }
            
            buffer = self._buffers[buffer_id]
            stats = buffer["stats"]
            data_queue = buffer["queue"]
            
            # 更新配置
            stats["max_size"] = max_size
            stats["mode"] = mode
            
            # 处理接收数据
            if raw_data_dict and "data" in raw_data_dict:
                data = raw_data_dict["data"]
                data_length = len(data)
                
                # 统计接收
                stats["received_count"] += 1
                stats["received_bytes"] += data_length
                stats["last_update"] = time.time()
                
                # 根据模式处理
                if mode == "queue":
                    # 队列模式：FIFO
                    if data_queue.full():
                        # 队列满，丢弃最旧的数据
                        try:
                            old_data, old_ts = data_queue.get_nowait()
                            stats["dropped_count"] += 1
                            stats["dropped_bytes"] += len(old_data["data"])
                        except queue.Empty:
                            pass
                    
                    try:
                        data_queue.put_nowait((raw_data_dict, time.time()))
                    except queue.Full:
                        stats["dropped_count"] += 1
                        stats["dropped_bytes"] += data_length
                
                elif mode == "stack":
                    # 栈模式：LIFO
                    if data_queue.full():
                        try:
                            old_data, old_ts = data_queue.get_nowait()
                            stats["dropped_count"] += 1
                            stats["dropped_bytes"] += len(old_data["data"])
                        except queue.Empty:
                            pass
                    
                    try:
                        data_queue.put_nowait((raw_data_dict, time.time()))
                    except queue.Full:
                        stats["dropped_count"] += 1
                        stats["dropped_bytes"] += data_length
                
                elif mode == "overwrite":
                    # 覆盖模式：始终保存最新数据
                    while not data_queue.empty():
                        try:
                            old_data, old_ts = data_queue.get_nowait()
                            stats["dropped_count"] += 1
                            stats["dropped_bytes"] += len(old_data["data"])
                        except queue.Empty:
                            break
                    
                    try:
                        data_queue.put_nowait((raw_data_dict, time.time()))
                    except queue.Full:
                        pass
                
                stats["current_size"] = data_queue.qsize()
                print(f"    [Buffer {buffer_id}] Received: {data_length} bytes, Queue: {stats['current_size']}/{max_size}")
            
            # 输出数据
            try:
                output_data, output_ts = data_queue.get_nowait()
                output_length = len(output_data["data"])
                
                # 统计发送
                stats["sent_count"] += 1
                stats["sent_bytes"] += output_length
                stats["current_size"] = data_queue.qsize()
                
                print(f"    [Buffer {buffer_id}] Sent: {output_length} bytes, Queue: {stats['current_size']}/{max_size}")
                
                return {
                    "RAW_DATA": output_data,
                    "BUFFER_STATS": {
                        "buffer_id": buffer_id,
                        "stats": stats.copy()
                    }
                }
            except queue.Empty:
                # 缓冲区为空
                return {
                    "BUFFER_STATS": {
                        "buffer_id": buffer_id,
                        "stats": stats.copy()
                    }
                }
    
    @classmethod
    def get_buffer_stats(cls, buffer_id: str) -> Dict:
        """获取缓冲区统计信息"""
        with cls._buffers_lock:
            if buffer_id in cls._buffers:
                return cls._buffers[buffer_id]["stats"].copy()
            return {}
    
    @classmethod
    def clear_buffer(cls, buffer_id: str):
        """清空指定缓冲区"""
        with cls._buffers_lock:
            if buffer_id in cls._buffers:
                buffer = cls._buffers[buffer_id]
                while not buffer["queue"].empty():
                    try:
                        buffer["queue"].get_nowait()
                    except queue.Empty:
                        break
                buffer["stats"]["current_size"] = 0
                print(f"    [Buffer {buffer_id}] Cleared")
    
    @classmethod
    def clear_all_buffers(cls):
        """清空所有缓冲区"""
        with cls._buffers_lock:
            for buffer_id in cls._buffers:
                cls.clear_buffer(buffer_id)


class BufferMonitorNode(NodeBase):
    """缓冲区监视器节点 - 显示缓冲区状态"""
    
    def __init__(self):
        super().__init__()
        self.name = "BufferMonitor"
        self.category = "signal/output"
        self.icon = "📊"
        self.inputs = ["BUFFER_STATS"]
        self.outputs = ["IMAGE"]
        self.description = "实时监视缓冲区状态"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "buffer_stats": ["BUFFER_STATS", {}],
                    "show_chart": ["BOOLEAN", {"default": True}],
                    "width": ["INT", {"default": 800, "min": 400, "max": 2048}],
                    "height": ["INT", {"default": 600, "min": 300, "max": 1536}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "BufferMonitor",
            "display_name": "缓冲区监视器",
            "description": "实时监视缓冲区状态",
            "category": "signal/output",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行缓冲区监视"""
        buffer_stats_dict = inputs.get("buffer_stats", {})
        show_chart = inputs.get("show_chart", True)
        width = inputs.get("width", 800)
        height = inputs.get("height", 600)
        
        if not buffer_stats_dict or "stats" not in buffer_stats_dict:
            print(f"    [X] No buffer stats to display")
            return {}
        
        buffer_id = buffer_stats_dict.get("buffer_id", "unknown")
        stats = buffer_stats_dict["stats"]
        
        # 控制台显示
        print(f"\n    ═══════════════════════════════════════")
        print(f"    📊 缓冲区监视器 - {buffer_id}")
        print(f"    ═══════════════════════════════════════")
        print(f"    接收统计:")
        print(f"      - 接收次数:   {stats['received_count']}")
        print(f"      - 接收字节:   {stats['received_bytes']:,} bytes ({stats['received_bytes']/1024:.2f} KB)")
        print(f"    发送统计:")
        print(f"      - 发送次数:   {stats['sent_count']}")
        print(f"      - 发送字节:   {stats['sent_bytes']:,} bytes ({stats['sent_bytes']/1024:.2f} KB)")
        print(f"    丢弃统计:")
        print(f"      - 丢弃次数:   {stats['dropped_count']}")
        print(f"      - 丢弃字节:   {stats['dropped_bytes']:,} bytes ({stats['dropped_bytes']/1024:.2f} KB)")
        print(f"    缓冲区状态:")
        print(f"      - 当前大小:   {stats['current_size']}/{stats['max_size']}")
        print(f"      - 使用率:     {stats['current_size']/stats['max_size']*100:.1f}%")
        print(f"      - 模式:       {stats['mode']}")
        print(f"    ═══════════════════════════════════════\n")
        
        # 生成可视化图表
        if show_chart and MATPLOTLIB_AVAILABLE:
            try:
                fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(width/100, height/100), dpi=100)
                
                # 1. 数据流统计
                categories = ['接收', '发送', '丢弃']
                counts = [stats['received_count'], stats['sent_count'], stats['dropped_count']]
                colors = ['#4CAF50', '#2196F3', '#F44336']
                ax1.bar(categories, counts, color=colors)
                ax1.set_title('数据包统计')
                ax1.set_ylabel('次数')
                ax1.grid(True, alpha=0.3)
                
                # 2. 字节统计
                bytes_data = [stats['received_bytes']/1024, stats['sent_bytes']/1024, stats['dropped_bytes']/1024]
                ax2.bar(categories, bytes_data, color=colors)
                ax2.set_title('数据量统计')
                ax2.set_ylabel('KB')
                ax2.grid(True, alpha=0.3)
                
                # 3. 缓冲区使用率
                usage_percent = stats['current_size'] / stats['max_size'] * 100
                ax3.pie([usage_percent, 100-usage_percent], 
                       labels=[f'已用 {stats["current_size"]}', f'空闲 {stats["max_size"]-stats["current_size"]}'],
                       colors=['#FF9800', '#E0E0E0'],
                       autopct='%1.1f%%',
                       startangle=90)
                ax3.set_title(f'缓冲区使用率 ({stats["mode"]} 模式)')
                
                # 4. 效率统计
                efficiency = (stats['sent_count'] / max(stats['received_count'], 1)) * 100
                drop_rate = (stats['dropped_count'] / max(stats['received_count'], 1)) * 100
                metrics = ['发送效率', '丢弃率']
                values = [efficiency, drop_rate]
                colors_eff = ['#4CAF50' if efficiency > 80 else '#FF9800', 
                             '#F44336' if drop_rate > 10 else '#4CAF50']
                ax4.barh(metrics, values, color=colors_eff)
                ax4.set_title('性能指标')
                ax4.set_xlabel('%')
                ax4.set_xlim(0, 100)
                ax4.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # 转换为PIL Image
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                image = Image.open(buf).copy()
                buf.close()
                plt.close(fig)
                
                print(f"    [OK] Generated buffer monitor chart: {image.size}")
                return {"IMAGE": image}
                
            except Exception as e:
                print(f"    [Error] Chart generation error: {e}")
                return {}
        
        return {}


class RawDataSaverNode(NodeBase):
    """原始数据保存节点 - 保存接收到的原始数据到文件"""
    
    def __init__(self):
        super().__init__()
        self.name = "RawDataSaver"
        self.category = "signal/output"
        self.icon = "💾"
        self.inputs = ["RAW_DATA"]
        self.outputs = []
        self.description = "保存原始网络数据到文件，便于调试"
        
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "raw_data": ["RAW_DATA", {}],
                    "filename": ["STRING", {"default": "raw_data"}],
                    "save_format": [["binary", "hex", "both"], {"default": "both"}],
                    "auto_timestamp": ["BOOLEAN", {"default": True}],
                    "append_mode": ["BOOLEAN", {"default": False}]
                }
            },
            "output": [],
            "output_is_list": [],
            "output_name": [],
            "name": "RawDataSaver",
            "display_name": "原始数据保存器",
            "description": "保存原始网络数据到文件，便于调试",
            "category": "signal/output",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行数据保存"""
        raw_data_dict = inputs.get("raw_data", {})
        filename = inputs.get("filename", "raw_data")
        save_format = inputs.get("save_format", "both")
        auto_timestamp = inputs.get("auto_timestamp", True)
        append_mode = inputs.get("append_mode", False)
        
        if not raw_data_dict or "data" not in raw_data_dict:
            print(f"    [X] No raw data to save")
            return {}
        
        data = raw_data_dict["data"]
        timestamp = raw_data_dict.get("timestamp", time.time())
        data_length = len(data)
        
        try:
            # 生成文件名
            if auto_timestamp:
                time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
                base_filename = f"{filename}_{time_str}"
            else:
                base_filename = filename
            
            # 确保output目录存在
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            saved_files = []
            
            # 保存二进制格式
            if save_format in ["binary", "both"]:
                bin_file = output_dir / f"{base_filename}.bin"
                mode = "ab" if append_mode else "wb"
                with open(bin_file, mode) as f:
                    f.write(data)
                saved_files.append(str(bin_file))
                print(f"    [OK] Saved binary: {bin_file} ({data_length} bytes)")
            
            # 保存十六进制文本格式
            if save_format in ["hex", "both"]:
                hex_file = output_dir / f"{base_filename}.hex"
                mode = "a" if append_mode else "w"
                with open(hex_file, mode, encoding='utf-8') as f:
                    # 写入时间戳和长度信息
                    f.write(f"# Timestamp: {timestamp} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))})\n")
                    f.write(f"# Length: {data_length} bytes\n")
                    f.write(f"# Data:\n")
                    
                    # 以16字节为一行显示十六进制数据
                    hex_str = data.hex()
                    for i in range(0, len(hex_str), 32):  # 每行16字节=32个十六进制字符
                        line = hex_str[i:i+32]
                        # 格式化为 XX XX XX XX ...
                        formatted_line = ' '.join([line[j:j+2] for j in range(0, len(line), 2)])
                        f.write(f"{i//2:08X}: {formatted_line}\n")
                    
                    f.write("\n" + "="*60 + "\n\n")
                
                saved_files.append(str(hex_file))
                print(f"    [OK] Saved hex: {hex_file} ({data_length} bytes)")
            
            # 显示保存摘要
            print(f"\n    ═══════════════════════════════════════")
            print(f"    💾 数据保存完成")
            print(f"    ═══════════════════════════════════════")
            print(f"    时间戳:     {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))}")
            print(f"    数据长度:   {data_length} bytes")
            print(f"    保存格式:   {save_format}")
            print(f"    保存文件:   {len(saved_files)} 个")
            for file in saved_files:
                print(f"      - {file}")
            print(f"    ═══════════════════════════════════════\n")
            
            return {
                "status": "saved",
                "files": saved_files,
                "length": data_length
            }
            
        except Exception as e:
            print(f"    [Error] Save error: {e}")
            import traceback
            traceback.print_exc()
            return {}


# =============================================================================
# 节点注册
# =============================================================================

SIGNAL_NODE_REGISTRY = {
    "NetworkReceiver": NetworkReceiverNode,
    "FrameParser": FrameParserNode,
    "DataConverter": DataConverterNode,
    "SpectrumAnalyzer": SpectrumAnalyzerNode,
    "AzimuthProcessor": AzimuthProcessorNode,
    "SignalClassifier": SignalClassifierNode,
    "FrequencyDetector": FrequencyDetectorNode,
    "SymbolRateAnalyzer": SymbolRateAnalyzerNode,
    "ConstellationDiagram": ConstellationDiagramNode,
    "SignalMonitor": SignalMonitorNode,
    "SignalInfoImage": SignalInfoImageNode,
    "DataBuffer": DataBufferNode,
    "BufferMonitor": BufferMonitorNode,
    "RawDataSaver": RawDataSaverNode,
}


def get_signal_node_instance(node_type: str) -> Optional[NodeBase]:
    """获取信号处理节点实例"""
    if node_type in SIGNAL_NODE_REGISTRY:
        return SIGNAL_NODE_REGISTRY[node_type]()
    return None


def get_all_signal_node_info() -> Dict[str, Any]:
    """获取所有信号处理节点信息"""
    result = {}
    for node_type, node_class in SIGNAL_NODE_REGISTRY.items():
        instance = node_class()
        result[node_type] = instance.get_node_info()
    return result


# 导出给主系统使用
__all__ = [
    'SIGNAL_NODE_REGISTRY',
    'get_signal_node_instance',
    'get_all_signal_node_info',
    'SignalFrame',
    'SignalData',
]

