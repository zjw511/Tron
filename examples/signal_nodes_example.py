"""
信号处理节点使用示例
演示如何使用signal_nodes.py中的各种节点
"""
import sys
import io

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import struct
import socket
import time

# 导入所有信号处理节点
from signal_nodes import (
    NetworkReceiverNode,
    FrameParserNode,
    DataConverterNode,
    SpectrumAnalyzerNode,
    AzimuthProcessorNode,
    SignalClassifierNode,
    FrequencyDetectorNode,
    SymbolRateAnalyzerNode,
    ConstellationDiagramNode,
    SignalMonitorNode,
    SignalFrame,
    SignalData,
    SIGNAL_NODE_REGISTRY,
    get_signal_node_instance,
    get_all_signal_node_info
)


# =============================================================================
# 测试数据生成器
# =============================================================================

class SignalDataGenerator:
    """生成模拟的信号数据用于测试"""
    
    @staticmethod
    def generate_test_iq_data(signal_type="QPSK", num_samples=1024, snr_db=20):
        """
        生成测试用的IQ数据
        
        Args:
            signal_type: 信号类型 ("QPSK", "QAM16", "FSK", "ASK")
            num_samples: 样本数量
            snr_db: 信噪比 (dB)
        
        Returns:
            np.ndarray: 复数IQ数据
        """
        # 生成基带信号
        if signal_type == "QPSK":
            # QPSK: 4个星座点
            symbols = np.random.choice([1+1j, 1-1j, -1+1j, -1-1j], size=num_samples//4)
        elif signal_type == "QAM16":
            # 16-QAM
            constellation = []
            for i in [-3, -1, 1, 3]:
                for q in [-3, -1, 1, 3]:
                    constellation.append(i + 1j*q)
            symbols = np.random.choice(constellation, size=num_samples//4)
        elif signal_type == "FSK":
            # FSK: 频移键控
            t = np.linspace(0, 1, num_samples)
            bits = np.random.randint(0, 2, size=100)
            signal = np.array([])
            for bit in bits:
                freq = 10 if bit else 5
                signal = np.append(signal, np.exp(1j * 2 * np.pi * freq * t[:num_samples//100]))
            return signal[:num_samples]
        elif signal_type == "ASK":
            # ASK: 振幅键控
            bits = np.random.randint(0, 2, size=num_samples)
            symbols = bits * (1 + 1j*0.1) + (1-bits) * (0.3 + 1j*0.1)
            return symbols
        else:
            symbols = np.random.randn(num_samples//4) + 1j*np.random.randn(num_samples//4)
        
        # 上采样（脉冲成形）
        samples_per_symbol = 4
        iq_data = np.repeat(symbols, samples_per_symbol)
        
        # 添加噪声
        signal_power = np.mean(np.abs(iq_data)**2)
        noise_power = signal_power / (10**(snr_db/10))
        noise = np.sqrt(noise_power/2) * (np.random.randn(len(iq_data)) + 1j*np.random.randn(len(iq_data)))
        
        return iq_data + noise
    
    @staticmethod
    def create_test_frame(iq_data, frame_id=1, frame_type=1):
        """
        创建测试用的数据帧
        
        Args:
            iq_data: IQ数据（复数数组）
            frame_id: 帧ID
            frame_type: 帧类型
        
        Returns:
            bytes: 打包好的数据帧
        """
        # 帧头: 0xAA55 (2 bytes)
        frame_header = b'\xAA\x55'
        
        # 帧ID: 4 bytes
        frame_id_bytes = struct.pack('<I', frame_id)
        
        # 时间戳: 8 bytes (double)
        timestamp_bytes = struct.pack('<d', time.time())
        
        # 帧类型: 2 bytes
        frame_type_bytes = struct.pack('<H', frame_type)
        
        # IQ数据转换为16位整数
        iq_int16 = np.zeros(len(iq_data)*2, dtype=np.int16)
        iq_int16[0::2] = np.clip(np.real(iq_data) * 32767, -32768, 32767).astype(np.int16)
        iq_int16[1::2] = np.clip(np.imag(iq_data) * 32767, -32768, 32767).astype(np.int16)
        data_bytes = iq_int16.tobytes()
        
        # 组装完整帧
        frame = frame_header + frame_id_bytes + timestamp_bytes + frame_type_bytes + data_bytes
        
        return frame
    
    @staticmethod
    def send_test_data_udp(host="127.0.0.1", port=8888, signal_type="QPSK", interval=0.1, count=10):
        """
        通过UDP发送测试数据
        
        Args:
            host: 目标主机
            port: 目标端口
            signal_type: 信号类型
            interval: 发送间隔（秒）
            count: 发送次数
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print(f"开始发送测试数据到 {host}:{port}")
        print(f"信号类型: {signal_type}, 间隔: {interval}s, 次数: {count}")
        
        for i in range(count):
            # 生成测试数据
            iq_data = SignalDataGenerator.generate_test_iq_data(signal_type, num_samples=1024)
            frame = SignalDataGenerator.create_test_frame(iq_data, frame_id=i+1)
            
            # 发送
            sock.sendto(frame, (host, port))
            print(f"  已发送帧 {i+1}/{count} ({len(frame)} 字节)")
            
            time.sleep(interval)
        
        sock.close()
        print("发送完成!")


# =============================================================================
# 使用示例
# =============================================================================

def example_1_basic_pipeline():
    """示例1: 基本的信号处理流水线"""
    print("\n" + "="*60)
    print("示例1: 基本信号处理流水线")
    print("="*60)
    
    # 生成测试数据
    iq_data = SignalDataGenerator.generate_test_iq_data("QPSK", num_samples=2048)
    frame_data = SignalDataGenerator.create_test_frame(iq_data)
    
    # 模拟网络接收的数据
    raw_data = {
        "data": frame_data,
        "timestamp": time.time(),
        "length": len(frame_data)
    }
    
    # 1. 帧解析
    parser = FrameParserNode()
    parsed_result = parser.execute({
        "raw_data": raw_data,
        "frame_header": "0xAA55",
        "header_size": 16,
        "byte_order": "little"
    }, "parser_1")
    
    if "FRAME" not in parsed_result:
        print("帧解析失败!")
        return
    
    # 2. 数据转换
    converter = DataConverterNode()
    converted_result = converter.execute({
        "frame": parsed_result["FRAME"],
        "data_format": "IQ_INT16",
        "sample_rate": 2.4e6,
        "center_frequency": 1.575e9
    }, "converter_1")
    
    if "SIGNAL_DATA" not in converted_result:
        print("数据转换失败!")
        return
    
    signal_data = converted_result["SIGNAL_DATA"]
    
    # 3. 信号分类
    classifier = SignalClassifierNode()
    classified_result = classifier.execute({
        "signal_data": signal_data,
        "method": "FEATURE_BASED"
    }, "classifier_1")
    
    signal_data = classified_result.get("SIGNAL_DATA", signal_data)
    
    # 4. 符号速率分析
    symbol_analyzer = SymbolRateAnalyzerNode()
    symbol_result = symbol_analyzer.execute({
        "signal_data": signal_data,
        "method": "AUTOCORR"
    }, "symbol_1")
    
    signal_data = symbol_result.get("SIGNAL_DATA", signal_data)
    
    # 5. 方位角处理
    azimuth_processor = AzimuthProcessorNode()
    azimuth_result = azimuth_processor.execute({
        "signal_data": signal_data,
        "algorithm": "PHASE_DIFF",
        "num_elements": 4,
        "element_spacing": 0.5
    }, "azimuth_1")
    
    signal_data = azimuth_result.get("SIGNAL_DATA", signal_data)
    
    # 6. 显示结果
    monitor = SignalMonitorNode()
    monitor.execute({"signal_data": signal_data}, "monitor_1")
    
    print("\n✓ 基本流水线执行完成!")


def example_2_visualization():
    """示例2: 信号可视化"""
    print("\n" + "="*60)
    print("示例2: 信号可视化")
    print("="*60)
    
    # 生成测试数据
    iq_data = SignalDataGenerator.generate_test_iq_data("QAM16", num_samples=4096, snr_db=25)
    
    # 创建信号数据对象
    signal_data = SignalData()
    signal_data.iq_data = iq_data
    signal_data.sample_rate = 2.4e6
    signal_data.frequency = 1.575e9
    signal_data.signal_type = "QAM16"
    signal_data.power = float(np.mean(np.abs(iq_data)**2))
    
    # 1. 频谱分析
    spectrum_analyzer = SpectrumAnalyzerNode()
    spectrum_result = spectrum_analyzer.execute({
        "signal_data": signal_data,
        "fft_size": 2048,
        "window": "hanning",
        "log_scale": True,
        "width": 1200,
        "height": 600
    }, "spectrum_1")
    
    if "IMAGE" in spectrum_result:
        spectrum_result["IMAGE"].save("output/spectrum_plot.png")
        print("  ✓ 频谱图已保存到 output/spectrum_plot.png")
    
    # 2. 星座图
    constellation = ConstellationDiagramNode()
    const_result = constellation.execute({
        "signal_data": signal_data,
        "max_points": 10000,
        "normalize": True,
        "show_density": True,
        "width": 800,
        "height": 800
    }, "const_1")
    
    if "IMAGE" in const_result:
        const_result["IMAGE"].save("output/constellation.png")
        print("  ✓ 星座图已保存到 output/constellation.png")
    
    # 3. 频点检测
    freq_detector = FrequencyDetectorNode()
    freq_result = freq_detector.execute({
        "signal_data": signal_data,
        "num_peaks": 5,
        "threshold_db": -40.0
    }, "freq_1")
    
    if "IMAGE" in freq_result:
        freq_result["IMAGE"].save("output/frequency_detection.png")
        print("  ✓ 频点检测图已保存到 output/frequency_detection.png")
    
    print("\n✓ 可视化完成!")


def example_3_network_receiver():
    """示例3: 网络接收器使用"""
    print("\n" + "="*60)
    print("示例3: 网络接收器")
    print("="*60)
    print("注意: 此示例需要另一个进程发送数据")
    print("可以运行: SignalDataGenerator.send_test_data_udp()")
    print("="*60)
    
    # 创建网络接收器
    receiver = NetworkReceiverNode()
    
    print("\n启动UDP接收器，监听 0.0.0.0:8888")
    print("等待数据... (将在5秒后超时)")
    
    # 配置接收器
    result = receiver.execute({
        "protocol": "UDP",
        "host": "0.0.0.0",
        "port": 8888,
        "buffer_size": 4096,
        "continuous": True,
        "timeout": 5.0
    }, "receiver_1")
    
    # 等待一段时间接收数据
    import time
    time.sleep(5)
    
    # 尝试获取数据
    for i in range(5):
        result = receiver.execute({
            "protocol": "UDP",
            "host": "0.0.0.0",
            "port": 8888,
            "buffer_size": 4096,
            "continuous": True,
            "timeout": 1.0
        }, "receiver_1")
        
        if result and "RAW_DATA" in result:
            print(f"  ✓ 接收到数据: {result['RAW_DATA']['length']} 字节")
        
        time.sleep(0.5)
    
    print("\n示例完成")


def example_4_complete_system():
    """示例4: 完整的信号处理系统"""
    print("\n" + "="*60)
    print("示例4: 完整信号处理系统")
    print("="*60)
    
    # 支持的信号类型
    signal_types = ["QPSK", "QAM16", "FSK", "ASK"]
    
    for sig_type in signal_types:
        print(f"\n处理 {sig_type} 信号...")
        
        # 生成测试数据
        iq_data = SignalDataGenerator.generate_test_iq_data(sig_type, num_samples=2048, snr_db=20)
        frame_data = SignalDataGenerator.create_test_frame(iq_data)
        
        # 完整处理流程
        raw_data = {"data": frame_data, "timestamp": time.time(), "length": len(frame_data)}
        
        # 解析
        parser = FrameParserNode()
        parsed = parser.execute({
            "raw_data": raw_data,
            "frame_header": "0xAA55",
            "header_size": 16,
            "byte_order": "little"
        }, f"parser_{sig_type}")
        
        if "FRAME" not in parsed:
            continue
        
        # 转换
        converter = DataConverterNode()
        converted = converter.execute({
            "frame": parsed["FRAME"],
            "data_format": "IQ_INT16",
            "sample_rate": 2.4e6,
            "center_frequency": 1.575e9
        }, f"conv_{sig_type}")
        
        if "SIGNAL_DATA" not in converted:
            continue
        
        signal_data = converted["SIGNAL_DATA"]
        
        # 分类
        classifier = SignalClassifierNode()
        signal_data = classifier.execute({
            "signal_data": signal_data,
            "method": "FEATURE_BASED"
        }, f"class_{sig_type}").get("SIGNAL_DATA", signal_data)
        
        # 生成星座图
        constellation = ConstellationDiagramNode()
        const_result = constellation.execute({
            "signal_data": signal_data,
            "max_points": 2000,
            "normalize": True,
            "show_density": False,
            "width": 600,
            "height": 600
        }, f"const_{sig_type}")
        
        if "IMAGE" in const_result:
            const_result["IMAGE"].save(f"output/constellation_{sig_type}.png")
            print(f"  ✓ {sig_type} 星座图已保存")
        
        # 显示信息
        print(f"  - 检测类型: {signal_data.signal_type}")
        print(f"  - 实际类型: {sig_type}")
        print(f"  - 功率: {10*np.log10(signal_data.power+1e-10):.2f} dB")
    
    print("\n✓ 完整系统测试完成!")


# =============================================================================
# 主程序
# =============================================================================

if __name__ == "__main__":
    print("="*60)
    print("   信号处理节点测试程序")
    print("="*60)
    
    # 运行示例
    try:
        example_1_basic_pipeline()
        example_2_visualization()
        # example_3_network_receiver()  # 需要外部数据源
        example_4_complete_system()
        
        print("\n" + "="*60)
        print("所有示例运行完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# 辅助工具函数
# =============================================================================

def send_test_data_continuously():
    """持续发送测试数据（用于测试网络接收器）"""
    print("持续发送测试数据模式")
    print("按 Ctrl+C 停止")
    
    try:
        while True:
            SignalDataGenerator.send_test_data_udp(
                host="127.0.0.1",
                port=8888,
                signal_type="QPSK",
                interval=0.5,
                count=10
            )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n已停止发送")


# 如果你想测试网络接收功能，可以在另一个终端运行：
# python signal_nodes_example.py
# 然后取消注释并运行 example_3_network_receiver()

