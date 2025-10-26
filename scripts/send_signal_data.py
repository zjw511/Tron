"""
Real-time Signal Data Sender
实时信号数据发送器 - 持续向ComfyUI的NetworkReceiver节点发送测试数据
"""
import sys
import io
import socket
import struct
import time
import numpy as np

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def generate_iq_signal(signal_type="QPSK", num_samples=1024, snr_db=20):
    """
    生成IQ测试信号
    
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
        samples_per_symbol = 4
        iq_data = np.repeat(symbols, samples_per_symbol)
        
    elif signal_type == "QAM16":
        # 16-QAM
        constellation = []
        for i in [-3, -1, 1, 3]:
            for q in [-3, -1, 1, 3]:
                constellation.append(i + 1j*q)
        symbols = np.random.choice(constellation, size=num_samples//4)
        samples_per_symbol = 4
        iq_data = np.repeat(symbols, samples_per_symbol)
        
    elif signal_type == "FSK":
        # FSK: 频移键控
        t = np.linspace(0, 1, num_samples)
        bits = np.random.randint(0, 2, size=100)
        signal = np.array([])
        for bit in bits:
            freq = 10 if bit else 5
            signal = np.append(signal, np.exp(1j * 2 * np.pi * freq * t[:num_samples//100]))
        iq_data = signal[:num_samples]
        
    elif signal_type == "ASK":
        # ASK: 振幅键控
        bits = np.random.randint(0, 2, size=num_samples)
        iq_data = bits * (1 + 1j*0.1) + (1-bits) * (0.3 + 1j*0.1)
        
    else:
        # 随机信号
        iq_data = np.random.randn(num_samples) + 1j*np.random.randn(num_samples)
    
    # 添加噪声
    signal_power = np.mean(np.abs(iq_data)**2)
    noise_power = signal_power / (10**(snr_db/10))
    noise = np.sqrt(noise_power/2) * (np.random.randn(len(iq_data)) + 1j*np.random.randn(len(iq_data)))
    
    return iq_data + noise


def create_data_frame(iq_data, frame_id=1, frame_type=1):
    """
    创建数据帧
    
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


def send_data_continuously(host="127.0.0.1", port=8888, signal_type="QPSK", 
                          interval=1.0, num_samples=1024, snr_db=20):
    """
    持续发送测试数据
    
    Args:
        host: 目标主机地址
        port: 目标端口
        signal_type: 信号类型
        interval: 发送间隔（秒）
        num_samples: 每次发送的样本数
        snr_db: 信噪比
    """
    print("="*60)
    print("   Real-time Signal Data Sender / 实时信号数据发送器")
    print("="*60)
    print(f"\nConfiguration / 配置:")
    print(f"  Target / 目标地址: {host}:{port}")
    print(f"  Signal Type / 信号类型: {signal_type}")
    print(f"  Samples / 样本数量: {num_samples}")
    print(f"  SNR / 信噪比: {snr_db} dB")
    print(f"  Interval / 发送间隔: {interval} sec")
    print(f"\nPress Ctrl+C to stop / 按 Ctrl+C 停止发送\n")
    print("="*60)
    
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    frame_count = 0
    
    try:
        while True:
            frame_count += 1
            
            # 生成IQ数据
            iq_data = generate_iq_signal(signal_type, num_samples, snr_db)
            
            # 创建数据帧
            frame = create_data_frame(iq_data, frame_id=frame_count, frame_type=1)
            
            # 发送数据
            try:
                sock.sendto(frame, (host, port))
                
                # 计算信号统计
                power = np.mean(np.abs(iq_data)**2)
                power_db = 10 * np.log10(power + 1e-10)
                
                # 显示状态
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Frame #{frame_count:04d} | {len(frame):6d} bytes | "
                      f"Power: {power_db:+.1f} dB | {signal_type}")
                
            except Exception as e:
                print(f"[ERROR] Send failed: {e}")
            
            # 等待指定间隔
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print(f"  Stopped / 已停止发送")
        print(f"  Total frames sent / 总共发送: {frame_count}")
        print("="*60)
    finally:
        sock.close()


def interactive_mode():
    """交互模式 - 让用户选择参数"""
    print("\n" + "="*60)
    print("   Real-time Signal Sender - Interactive Mode")
    print("   实时信号数据发送器 - 交互模式")
    print("="*60)
    
    # 选择信号类型
    print("\nSelect signal type / 选择信号类型:")
    print("  1. QPSK   (Phase Shift Keying / 相移键控)")
    print("  2. QAM16  (16-Quadrature Amplitude Modulation / 16-正交振幅调制)")
    print("  3. FSK    (Frequency Shift Keying / 频移键控)")
    print("  4. ASK    (Amplitude Shift Keying / 幅移键控)")
    
    signal_types = {
        "1": "QPSK",
        "2": "QAM16",
        "3": "FSK",
        "4": "ASK"
    }
    
    choice = input("\nChoice / 请选择 [1-4] (default/默认 1): ").strip() or "1"
    signal_type = signal_types.get(choice, "QPSK")
    
    # 目标地址
    host = input("\nTarget host / 目标地址 (default/默认 127.0.0.1): ").strip() or "127.0.0.1"
    
    # 目标端口
    port_str = input("Target port / 目标端口 (default/默认 8888): ").strip() or "8888"
    try:
        port = int(port_str)
    except:
        port = 8888
    
    # 发送间隔
    interval_str = input("Send interval (sec) / 发送间隔(秒) (default/默认 1.0): ").strip() or "1.0"
    try:
        interval = float(interval_str)
    except:
        interval = 1.0
    
    # 样本数量
    samples_str = input("Number of samples / 样本数量 (default/默认 1024): ").strip() or "1024"
    try:
        num_samples = int(samples_str)
    except:
        num_samples = 1024
    
    # 信噪比
    snr_str = input("SNR (dB) / 信噪比(dB) (default/默认 20): ").strip() or "20"
    try:
        snr_db = float(snr_str)
    except:
        snr_db = 20
    
    print("\n" + "="*60)
    
    # 开始发送
    send_data_continuously(host, port, signal_type, interval, num_samples, snr_db)


def quick_start():
    """快速启动 - 使用默认参数"""
    send_data_continuously(
        host="127.0.0.1",
        port=8888,
        signal_type="QPSK",
        interval=1.0,
        num_samples=1024,
        snr_db=20
    )


if __name__ == "__main__":
    print("\n" + "="*60)
    print("   ComfyUI Signal Processing - Data Sender")
    print("   ComfyUI 信号处理节点 - 数据发送器")
    print("="*60)
    print("\nStart mode / 启动模式:")
    print("  1. Quick Start / 快速启动 (use default params / 使用默认参数)")
    print("  2. Interactive Mode / 交互模式 (custom params / 自定义参数)")
    print("  3. Exit / 退出")
    
    mode = input("\nChoice / 请选择 [1-3]: ").strip()
    
    if mode == "1":
        quick_start()
    elif mode == "2":
        interactive_mode()
    else:
        print("\nExited / 已退出")

