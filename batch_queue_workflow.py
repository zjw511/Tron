"""
批量执行ComfyUI工作流
绕过前端的100次限制，直接通过API调用
"""
import requests
import json
import time
from pathlib import Path

# 配置
COMFYUI_URL = "http://127.0.0.1:8188"
API_PROMPT = f"{COMFYUI_URL}/prompt"

def convert_litegraph_to_api(litegraph_data):
    """提示用户如何获取API格式的工作流"""
    print("\n" + "="*60)
    print("[!] 当前工作流是LiteGraph格式（UI保存格式）")
    print("    需要转换为API格式才能用此脚本执行")
    print("="*60)
    print("\n[方法] 如何获取API格式工作流：")
    print("\n方法1: 通过浏览器开发者工具（推荐）")
    print("  1. 打开ComfyUI界面")
    print("  2. 按F12打开开发者工具")
    print("  3. 切换到 Network (网络) 标签")
    print("  4. 在ComfyUI中点击 'Queue Prompt' 执行一次工作流")
    print("  5. 在Network中找到 '/prompt' 请求")
    print("  6. 右键 -> Copy -> Copy Request Payload (复制请求负载)")
    print("  7. 将复制的内容保存为新的JSON文件")
    print("\n方法2: 启用API保存模式（如果ComfyUI支持）")
    print("  1. 在ComfyUI设置中查找 'API Format' 选项")
    print("  2. 启用后重新保存工作流")
    print("\n方法3: 使用现有工作流手动创建")
    print("  直接在界面点击 Queue Prompt，脚本会自动重复执行")
    print("="*60)
    return None

def load_workflow(workflow_file="user/workflows/signal1.json"):
    """加载工作流JSON文件"""
    workflow_path = Path(workflow_file)
    if not workflow_path.exists():
        print(f"[X] 工作流文件不存在: {workflow_file}")
        print("[提示] 在ComfyUI界面保存工作流后，文件会在 user/workflows/ 目录")
        return None
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查数据格式
    if not isinstance(data, dict):
        print(f"[X] 工作流格式错误：应该是字典类型")
        return None
    
    # 情况1: LiteGraph格式（包含nodes数组）
    # 这是从ComfyUI界面保存的格式
    if "nodes" in data and isinstance(data["nodes"], list):
        print("[!] 检测到LiteGraph格式，正在转换为API格式...")
        return convert_litegraph_to_api(data)
    
    # 情况2: API格式包含prompt键
    if "prompt" in data:
        return data["prompt"]
    
    # 情况3: 直接是节点字典（所有值都是字典）
    if all(isinstance(v, dict) and "class_type" in v for k, v in data.items() if isinstance(k, str) and k.isdigit()):
        return data
    
    # 其他情况
    print(f"[!] 无法识别的工作流格式")
    print(f"   包含的键: {list(data.keys())}")
    return None

def queue_workflow(workflow_data):
    """提交工作流到队列"""
    try:
        # ComfyUI API期望的格式：{"prompt": workflow_dict, "client_id": ...}
        # workflow_data应该是工作流的节点字典，不是整个文件内容
        
        # 如果workflow_data包含"prompt"键，说明是完整的API格式
        if isinstance(workflow_data, dict) and "prompt" in workflow_data:
            payload = workflow_data
        else:
            # 否则，workflow_data就是节点字典
            payload = {"prompt": workflow_data}
        
        response = requests.post(API_PROMPT, json=payload)
        if response.status_code == 200:
            result = response.json()
            return True, result.get('prompt_id')
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def batch_execute(workflow_data, count=500, delay=0.1):
    """批量执行工作流"""
    print(f"\n[>>] 开始批量执行工作流")
    print(f"   目标次数: {count}")
    print(f"   间隔时间: {delay}秒")
    print(f"   预计时间: {count * delay / 60:.1f}分钟")
    print(f"\n按 Ctrl+C 可以随时停止\n")
    
    success_count = 0
    fail_count = 0
    
    try:
        for i in range(count):
            success, result = queue_workflow(workflow_data)
            
            if success:
                success_count += 1
                print(f"[OK] [{i+1}/{count}] 成功提交 (ID: {result})")
            else:
                fail_count += 1
                print(f"[X] [{i+1}/{count}] 失败: {result}")
            
            # 延迟，避免过快
            if i < count - 1:  # 最后一次不需要延迟
                time.sleep(delay)
                
    except KeyboardInterrupt:
        print(f"\n\n[!] 用户中断")
    
    print(f"\n" + "="*50)
    print(f"[总结] 执行完成")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")
    print(f"   总计: {success_count + fail_count}/{count}")
    print(f"="*50 + "\n")

def main():
    print("="*60)
    print("  ComfyUI 批量工作流执行器")
    print("  绕过前端100次限制")
    print("="*60)
    
    # 1. 加载工作流
    print("\n[*] 加载工作流...")
    workflow = load_workflow()
    
    if not workflow:
        print("\n[提示] 使用方法：")
        print("   1. 在ComfyUI界面创建/打开工作流")
        print("   2. 点击 Save 保存工作流")
        print("   3. 运行此脚本")
        return
    
    print(f"[OK] 工作流加载成功")
    print(f"  节点数: {len(workflow)}")
    
    # 2. 询问执行次数
    print("\n[配置] 批量执行参数")
    try:
        count = int(input("执行次数 (默认500): ") or "500")
        delay = float(input("间隔秒数 (默认0.1): ") or "0.1")
    except ValueError:
        print("[!] 输入错误，使用默认值")
        count = 500
        delay = 0.1
    
    # 3. 确认
    print(f"\n[信息] 确认信息:")
    print(f"   ComfyUI地址: {COMFYUI_URL}")
    print(f"   执行次数: {count}")
    print(f"   间隔时间: {delay}秒")
    print(f"   预计耗时: {count * delay / 60:.1f}分钟")
    
    confirm = input("\n确认执行? (y/n): ").lower()
    if confirm != 'y':
        print("[!] 已取消")
        return
    
    # 4. 执行
    batch_execute(workflow, count, delay)

if __name__ == "__main__":
    main()

