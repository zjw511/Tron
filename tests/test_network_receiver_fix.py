"""
测试NetworkReceiver线程重复创建问题的修复
"""
import sys
import io

# 设置UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from signal_nodes import NetworkReceiverNode
import time

print("="*60)
print("  NetworkReceiver线程重复创建问题修复测试")
print("="*60)

# 测试1: 多次执行同一配置
print("\n[测试1] 多次执行同一配置 (UDP:0.0.0.0:8888)")
print("-"*60)

node = NetworkReceiverNode()

for i in range(5):
    print(f"\n执行 #{i+1}:")
    result = node.execute({
        "protocol": "UDP",
        "host": "0.0.0.0",
        "port": 8888,
        "continuous": True,
        "buffer_size": 4096,
        "timeout": 1.0
    }, f"node_{i}")
    
    # 检查活动接收器数量
    receiver_count = len(NetworkReceiverNode._active_receivers)
    print(f"  当前活动接收器数量: {receiver_count}")
    
    # 检查线程状态
    for key, receiver in NetworkReceiverNode._active_receivers.items():
        thread_alive = receiver["thread"].is_alive()
        queue_size = receiver["queue"].qsize()
        print(f"  接收器 '{key}': 线程活跃={thread_alive}, 队列={queue_size}")
    
    time.sleep(0.1)

# 验证
print("\n" + "="*60)
print("验证结果:")
if len(NetworkReceiverNode._active_receivers) == 1:
    print("  ✓ 只有1个接收器（预期）")
else:
    print(f"  ✗ 有{len(NetworkReceiverNode._active_receivers)}个接收器（应该是1个）")

receiver = list(NetworkReceiverNode._active_receivers.values())[0]
if receiver["thread"].is_alive():
    print("  ✓ 线程仍在运行（预期）")
else:
    print("  ✗ 线程已停止（不正常）")

print("="*60)

# 测试2: 不同配置创建不同接收器
print("\n[测试2] 不同配置创建不同接收器")
print("-"*60)

node2 = NetworkReceiverNode()
result = node2.execute({
    "protocol": "UDP",
    "host": "0.0.0.0",
    "port": 9999,  # 不同端口
    "continuous": True,
    "buffer_size": 4096,
    "timeout": 1.0
}, "node2")

print(f"\n当前活动接收器数量: {len(NetworkReceiverNode._active_receivers)}")
for key in NetworkReceiverNode._active_receivers.keys():
    print(f"  - {key}")

# 验证
print("\n" + "="*60)
print("验证结果:")
if len(NetworkReceiverNode._active_receivers) == 2:
    print("  ✓ 有2个接收器（不同端口，预期）")
else:
    print(f"  ✗ 有{len(NetworkReceiverNode._active_receivers)}个接收器（应该是2个）")

print("="*60)

# 测试3: 清理所有接收器
print("\n[测试3] 清理所有接收器")
print("-"*60)

NetworkReceiverNode.stop_all_receivers()
time.sleep(0.5)  # 等待线程完全停止

print(f"清理后活动接收器数量: {len(NetworkReceiverNode._active_receivers)}")

# 验证
print("\n" + "="*60)
print("验证结果:")
if len(NetworkReceiverNode._active_receivers) == 0:
    print("  ✓ 所有接收器已清理（预期）")
else:
    print(f"  ✗ 还有{len(NetworkReceiverNode._active_receivers)}个接收器（应该是0个）")

print("="*60)

# 最终总结
print("\n" + "="*60)
print("  测试完成")
print("="*60)
print("\n如果所有测试都显示 ✓，则修复成功！")
print("\n注意: 由于没有实际数据发送，队列为空是正常的。")
print("在实际使用中，当有数据发送到端口时，队列会有数据。\n")

