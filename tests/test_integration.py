"""
测试信号处理节点集成到ComfyUI
"""
import sys
import io

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("="*60)
print("  测试信号处理节点集成")
print("="*60)

# 测试1: 导入基础节点
print("\n[测试1] 导入基础节点系统...")
try:
    from nodes import get_all_node_info, get_node_instance, NODE_REGISTRY
    print(f"  ✓ 基础节点导入成功")
    print(f"  ✓ 基础节点数量: {len(NODE_REGISTRY)}")
    print(f"  ✓ 基础节点列表: {list(NODE_REGISTRY.keys())}")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    sys.exit(1)

# 测试2: 导入信号处理节点
print("\n[测试2] 导入信号处理节点系统...")
try:
    from signal_nodes import (
        SIGNAL_NODE_REGISTRY,
        get_signal_node_instance,
        get_all_signal_node_info
    )
    print(f"  ✓ 信号处理节点导入成功")
    print(f"  ✓ 信号处理节点数量: {len(SIGNAL_NODE_REGISTRY)}")
    print(f"  ✓ 信号处理节点列表: {list(SIGNAL_NODE_REGISTRY.keys())}")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    sys.exit(1)

# 测试3: 合并节点信息
print("\n[测试3] 合并节点信息...")
try:
    all_nodes = get_all_node_info()
    signal_nodes = get_all_signal_node_info()
    all_nodes.update(signal_nodes)
    
    print(f"  ✓ 合并成功")
    print(f"  ✓ 总节点数: {len(all_nodes)}")
    print(f"  ✓ 节点列表:")
    
    # 按类别分组
    categories = {}
    for node_name, node_info in all_nodes.items():
        category = node_info.get('category', 'unknown')
        if category not in categories:
            categories[category] = []
        categories[category].append(node_name)
    
    for category, nodes in sorted(categories.items()):
        print(f"    [{category}]: {', '.join(nodes)}")
    
except Exception as e:
    print(f"  ✗ 合并失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试4: 获取节点实例
print("\n[测试4] 测试节点实例化...")
test_nodes = [
    ("LoadImage", False),
    ("NetworkReceiver", True),
    ("SpectrumAnalyzer", True),
    ("SignalMonitor", True)
]

for node_name, is_signal_node in test_nodes:
    try:
        if is_signal_node:
            instance = get_signal_node_instance(node_name)
        else:
            instance = get_node_instance(node_name)
        
        if instance:
            print(f"  ✓ {node_name}: {instance.__class__.__name__}")
        else:
            print(f"  ✗ {node_name}: 实例化失败")
    except Exception as e:
        print(f"  ✗ {node_name}: {e}")

# 测试5: 验证节点信息完整性
print("\n[测试5] 验证节点信息完整性...")
required_fields = ['input', 'output', 'name', 'category']
errors = 0

for node_name, node_info in all_nodes.items():
    missing = [f for f in required_fields if f not in node_info]
    if missing:
        print(f"  ✗ {node_name} 缺少字段: {missing}")
        errors += 1

if errors == 0:
    print(f"  ✓ 所有 {len(all_nodes)} 个节点信息完整")
else:
    print(f"  ✗ {errors} 个节点信息不完整")

# 总结
print("\n" + "="*60)
print("  测试总结")
print("="*60)
print(f"  基础节点: {len(NODE_REGISTRY)} 个")
print(f"  信号节点: {len(SIGNAL_NODE_REGISTRY)} 个")
print(f"  总计: {len(all_nodes)} 个")
print(f"  状态: {'✓ 所有测试通过' if errors == 0 else '✗ 存在错误'}")
print("="*60)

if errors == 0:
    print("\n🎉 信号处理节点已成功集成到ComfyUI！")
    print("\n下一步:")
    print("  1. 启动服务器: python full_server.py")
    print("  2. 打开浏览器: http://127.0.0.1:8188")
    print("  3. 在节点列表中查找信号处理节点")
    sys.exit(0)
else:
    sys.exit(1)

