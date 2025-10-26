"""
信号处理节点快速测试脚本
用于验证各个节点的基本功能
"""
import sys
import os
import io

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试1: 验证所有导入"""
    print("\n[测试1] 验证导入...")
    try:
        import signal_nodes
        print("  ✓ signal_nodes 导入成功")
        
        import numpy as np
        print("  ✓ numpy 可用")
        
        try:
            import matplotlib
            print("  ✓ matplotlib 可用")
        except ImportError:
            print("  ⚠ matplotlib 不可用 (可视化节点将受限)")
        
        try:
            import scipy
            print("  ✓ scipy 可用")
        except ImportError:
            print("  ⚠ scipy 不可用 (部分分析功能将受限)")
        
        return True
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False


def test_node_registration():
    """测试2: 验证节点注册"""
    print("\n[测试2] 验证节点注册...")
    try:
        from signal_nodes import SIGNAL_NODE_REGISTRY, get_signal_node_instance
        
        expected_nodes = [
            "NetworkReceiver",
            "FrameParser",
            "DataConverter",
            "SpectrumAnalyzer",
            "AzimuthProcessor",
            "SignalClassifier",
            "FrequencyDetector",
            "SymbolRateAnalyzer",
            "ConstellationDiagram",
            "SignalMonitor"
        ]
        
        for node_name in expected_nodes:
            if node_name in SIGNAL_NODE_REGISTRY:
                instance = get_signal_node_instance(node_name)
                if instance:
                    print(f"  ✓ {node_name} 注册成功")
                else:
                    print(f"  ✗ {node_name} 实例化失败")
                    return False
            else:
                print(f"  ✗ {node_name} 未注册")
                return False
        
        print(f"  ✓ 所有 {len(expected_nodes)} 个节点已正确注册")
        return True
    except Exception as e:
        print(f"  ✗ 节点注册验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_structures():
    """测试3: 验证数据结构"""
    print("\n[测试3] 验证数据结构...")
    try:
        from signal_nodes import SignalFrame, SignalData
        import numpy as np
        
        # 测试 SignalFrame
        frame = SignalFrame()
        frame.frame_id = 1
        frame.timestamp = 123.456
        frame.frame_type = 1
        frame.data_length = 100
        frame.raw_data = b'test data'
        frame.parsed = True
        print(f"  ✓ SignalFrame: {frame}")
        
        # 测试 SignalData
        signal = SignalData()
        signal.iq_data = np.random.randn(100) + 1j*np.random.randn(100)
        signal.frequency = 1.575e9
        signal.sample_rate = 2.4e6
        signal.power = float(np.mean(np.abs(signal.iq_data)**2))
        signal.signal_type = "QPSK"
        signal.symbol_rate = 1e6
        print(f"  ✓ SignalData: freq={signal.frequency/1e6:.1f}MHz, type={signal.signal_type}")
        
        return True
    except Exception as e:
        print(f"  ✗ 数据结构验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_nodes():
    """测试4: 测试基本节点功能"""
    print("\n[测试4] 测试基本节点功能...")
    try:
        from signal_nodes import SignalFrame, SignalData, DataConverterNode, SignalClassifierNode, AzimuthProcessorNode, SignalMonitorNode
        import numpy as np
        import struct
        import time
        
        # 4.1 测试数据转换器
        print("  [4.1] 测试 DataConverter...")
        frame = SignalFrame()
        frame.frame_id = 1
        frame.parsed = True
        
        # 创建测试IQ数据（16位整数格式）
        iq_samples = 128
        i_data = (np.random.randn(iq_samples) * 16384).astype(np.int16)
        q_data = (np.random.randn(iq_samples) * 16384).astype(np.int16)
        iq_interleaved = np.empty(iq_samples * 2, dtype=np.int16)
        iq_interleaved[0::2] = i_data
        iq_interleaved[1::2] = q_data
        frame.raw_data = iq_interleaved.tobytes()
        frame.data_length = len(frame.raw_data)
        
        converter = DataConverterNode()
        result = converter.execute({
            "frame": frame,
            "data_format": "IQ_INT16",
            "sample_rate": 2.4e6,
            "center_frequency": 1.575e9
        }, "test_conv")
        
        if "SIGNAL_DATA" in result:
            signal = result["SIGNAL_DATA"]
            print(f"    ✓ 转换成功: {len(signal.iq_data)} 样本")
        else:
            print("    ✗ 转换失败")
            return False
        
        # 4.2 测试信号分类器
        print("  [4.2] 测试 SignalClassifier...")
        classifier = SignalClassifierNode()
        result = classifier.execute({
            "signal_data": signal,
            "method": "FEATURE_BASED"
        }, "test_class")
        
        if "SIGNAL_DATA" in result:
            signal = result["SIGNAL_DATA"]
            print(f"    ✓ 分类结果: {signal.signal_type}")
        else:
            print("    ✗ 分类失败")
            return False
        
        # 4.3 测试方位角处理器
        print("  [4.3] 测试 AzimuthProcessor...")
        azimuth = AzimuthProcessorNode()
        result = azimuth.execute({
            "signal_data": signal,
            "algorithm": "PHASE_DIFF",
            "num_elements": 4,
            "element_spacing": 0.5
        }, "test_azimuth")
        
        if "SIGNAL_DATA" in result:
            signal = result["SIGNAL_DATA"]
            print(f"    ✓ 方位角: {signal.azimuth:.1f}°")
        else:
            print("    ✗ 方位角处理失败")
            return False
        
        # 4.4 测试信号监视器
        print("  [4.4] 测试 SignalMonitor...")
        monitor = SignalMonitorNode()
        result = monitor.execute({
            "signal_data": signal
        }, "test_monitor")
        
        if result:
            print("    ✓ 监视器显示成功")
        else:
            print("    ⚠ 监视器返回为空")
        
        print("  ✓ 基本节点功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ✗ 基本节点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visualization_nodes():
    """测试5: 测试可视化节点"""
    print("\n[测试5] 测试可视化节点...")
    
    try:
        import matplotlib
    except ImportError:
        print("  ⚠ matplotlib不可用，跳过可视化测试")
        return True
    
    try:
        from signal_nodes import SignalData, SpectrumAnalyzerNode, ConstellationDiagramNode
        import numpy as np
        
        # 创建测试信号数据
        signal = SignalData()
        signal.iq_data = np.random.randn(1024) + 1j*np.random.randn(1024)
        signal.frequency = 1.575e9
        signal.sample_rate = 2.4e6
        signal.power = float(np.mean(np.abs(signal.iq_data)**2))
        signal.signal_type = "QPSK"
        
        # 5.1 测试频谱分析仪
        print("  [5.1] 测试 SpectrumAnalyzer...")
        spectrum = SpectrumAnalyzerNode()
        result = spectrum.execute({
            "signal_data": signal,
            "fft_size": 512,
            "window": "hanning",
            "log_scale": True,
            "width": 800,
            "height": 600
        }, "test_spectrum")
        
        if "IMAGE" in result:
            img = result["IMAGE"]
            print(f"    ✓ 频谱图生成: {img.size}")
        else:
            print("    ✗ 频谱图生成失败")
            return False
        
        # 5.2 测试星座图
        print("  [5.2] 测试 ConstellationDiagram...")
        constellation = ConstellationDiagramNode()
        result = constellation.execute({
            "signal_data": signal,
            "max_points": 1000,
            "normalize": True,
            "show_density": False,
            "width": 600,
            "height": 600
        }, "test_const")
        
        if "IMAGE" in result:
            img = result["IMAGE"]
            print(f"    ✓ 星座图生成: {img.size}")
        else:
            print("    ✗ 星座图生成失败")
            return False
        
        print("  ✓ 可视化节点测试通过")
        return True
        
    except Exception as e:
        print(f"  ✗ 可视化节点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frame_parser():
    """测试6: 测试帧解析器"""
    print("\n[测试6] 测试帧解析器...")
    try:
        from signal_nodes import FrameParserNode
        import struct
        import time
        
        # 构造测试帧
        frame_data = b''
        frame_data += b'\xAA\x55'  # 帧头
        frame_data += struct.pack('<I', 12345)  # 帧ID
        frame_data += struct.pack('<d', time.time())  # 时间戳
        frame_data += struct.pack('<H', 1)  # 帧类型
        frame_data += b'test payload data'  # 数据部分
        
        raw_data = {
            "data": frame_data,
            "timestamp": time.time(),
            "length": len(frame_data)
        }
        
        parser = FrameParserNode()
        result = parser.execute({
            "raw_data": raw_data,
            "frame_header": "0xAA55",
            "header_size": 16,
            "byte_order": "little"
        }, "test_parser")
        
        if "FRAME" in result:
            frame = result["FRAME"]
            if frame.parsed:
                print(f"  ✓ 帧解析成功: ID={frame.frame_id}, Type={frame.frame_type}")
                return True
            else:
                print("  ✗ 帧解析标志为False")
                return False
        else:
            print("  ✗ 帧解析失败")
            return False
            
    except Exception as e:
        print(f"  ✗ 帧解析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_node_info():
    """测试7: 验证节点信息"""
    print("\n[测试7] 验证节点信息...")
    try:
        from signal_nodes import get_all_signal_node_info
        
        all_info = get_all_signal_node_info()
        
        if not all_info:
            print("  ✗ 未获取到节点信息")
            return False
        
        print(f"  ✓ 获取到 {len(all_info)} 个节点的信息")
        
        # 验证每个节点的信息完整性
        required_fields = ["input", "output", "name", "display_name", "category"]
        
        for node_name, info in all_info.items():
            missing_fields = [field for field in required_fields if field not in info]
            if missing_fields:
                print(f"  ✗ {node_name} 缺少字段: {missing_fields}")
                return False
        
        print("  ✓ 所有节点信息完整")
        return True
        
    except Exception as e:
        print(f"  ✗ 节点信息验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("="*60)
    print("   信号处理节点 - 自动化测试")
    print("="*60)
    
    tests = [
        ("导入测试", test_imports),
        ("节点注册", test_node_registration),
        ("数据结构", test_data_structures),
        ("基本节点", test_basic_nodes),
        ("可视化节点", test_visualization_nodes),
        ("帧解析器", test_frame_parser),
        ("节点信息", test_node_info),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n测试 '{test_name}' 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("   测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status:8} - {test_name}")
    
    print("="*60)
    print(f"  总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("  🎉 所有测试通过！")
        return True
    else:
        print(f"  ⚠ {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

