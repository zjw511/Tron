"""
Full-Featured ComfyUI Server
完整功能的ComfyUI服务器 - 使用官方前端 + 模块化节点系统
"""
import asyncio
import os
import sys
import json
import uuid
from pathlib import Path
from aiohttp import web
from PIL import Image
import io
import base64
import importlib.resources

# 导入节点系统
from nodes import get_all_node_info, get_node_instance, NODE_REGISTRY

# 导入信号处理节点系统
try:
    from signal_nodes import (
        SIGNAL_NODE_REGISTRY,
        get_signal_node_instance,
        get_all_signal_node_info
    )
    SIGNAL_NODES_AVAILABLE = True
    print("[OK] Signal processing nodes loaded successfully")
except ImportError as e:
    SIGNAL_NODES_AVAILABLE = False
    print(f"[Warning] Signal processing nodes not available: {e}")

# 修复Windows asyncio问题
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 创建必要目录
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")
USER_DIR = Path("user")
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
USER_DIR.mkdir(exist_ok=True)

# WebSocket客户端集合
websocket_clients = set()

# 工作流历史记录
workflow_history = {}


def get_frontend_path():
    """获取ComfyUI前端包路径"""
    try:
        import comfyui_frontend_package
        static_path = importlib.resources.files(comfyui_frontend_package) / "static"
        return str(static_path)
    except ImportError:
        print("[X] comfyui_frontend_package not installed!")
        print("Install: pip install comfyui-frontend-package")
        return None


# CORS中间件
@web.middleware
async def cors_middleware(request, handler):
    """CORS中间件 - 允许跨域请求"""
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
    
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, PUT, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ==================== 核心API处理器 ====================

async def handle_prompt(request):
    """处理工作流执行请求"""
    try:
        data = await request.json()
        print(f"\n[>>] Received workflow request")
        
        # 获取prompt数据
        prompt_data = data.get('prompt', data)
        
        # 验证prompt_data是字典类型
        if not isinstance(prompt_data, dict):
            print(f"[X] Invalid prompt_data type: {type(prompt_data)}")
            return web.json_response(
                {"error": f"Invalid prompt data: expected dict, got {type(prompt_data).__name__}"}, 
                status=400
            )
        
        # 验证prompt_data包含节点
        if not prompt_data:
            print(f"[X] Empty prompt_data")
            return web.json_response({"error": "Empty workflow"}, status=400)
        
        # 生成prompt ID
        prompt_id = f"prompt-{uuid.uuid4().hex[:8]}"
        
        # 执行工作流
        result = await execute_workflow(prompt_data, prompt_id)
        
        # 保存到历史
        workflow_history[prompt_id] = {
            "prompt": prompt_data,
            "outputs": result.get("node_outputs", {})
        }
        
        # 通过WebSocket发送执行结果
        if websocket_clients and "node_outputs" in result:
            for node_id, output in result["node_outputs"].items():
                if output.get("ui"):
                    ws_message = {
                        "type": "executed",
                        "data": {
                            "node": node_id,
                            "output": output["ui"],
                            "prompt_id": prompt_id
                        }
                    }
                    print(f"[>>] Sending WebSocket message for node {node_id}")
                    await broadcast_message(ws_message)
        
        # 返回ComfyUI标准响应
        return web.json_response({
            "prompt_id": prompt_id,
            "number": len(workflow_history),
            "node_errors": result.get("errors", {})
        })
        
    except Exception as e:
        print(f"[X] Error in handle_prompt: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def handle_object_info(request):
    """返回所有节点信息 - 包括基础节点和信号处理节点"""
    print("[>>] API: /object_info requested")
    
    # 获取基础节点信息
    node_info = get_all_node_info()
    
    # 合并信号处理节点信息
    if SIGNAL_NODES_AVAILABLE:
        signal_node_info = get_all_signal_node_info()
        node_info.update(signal_node_info)
        print(f"    [OK] Loaded {len(NODE_REGISTRY)} basic nodes + {len(SIGNAL_NODE_REGISTRY)} signal nodes")
    else:
        print(f"    [OK] Loaded {len(NODE_REGISTRY)} basic nodes")
    
    return web.json_response(node_info)


async def handle_queue(request):
    """队列API"""
    return web.json_response({
        "queue_running": [],
        "queue_pending": []
    })


async def handle_history(request):
    """历史API"""
    prompt_id = request.match_info.get('prompt_id')
    if prompt_id:
        if prompt_id in workflow_history:
            return web.json_response({prompt_id: workflow_history[prompt_id]})
        else:
            return web.json_response({})
    else:
        return web.json_response(workflow_history)


async def handle_embeddings(request):
    """嵌入API"""
    return web.json_response([])


async def handle_extensions(request):
    """扩展API"""
    return web.json_response([])


async def handle_system_stats(request):
    """系统状态"""
    return web.json_response({
        "system": {
            "os": "windows" if sys.platform == 'win32' else sys.platform,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}"
        },
        "devices": [
            {"name": "cpu", "type": "cpu"}
        ]
    })


# ==================== 用户相关API ====================

async def handle_users(request):
    """用户API"""
    if request.method == 'GET':
        return web.json_response({
            "storage": "server",
            "migrated": True
        })
    elif request.method == 'POST':
        return web.json_response({"status": "ok"})
    return web.json_response({"error": "Method not allowed"}, status=405)


async def handle_user_config(request):
    """用户配置API"""
    if request.method == 'GET':
        return web.json_response({
            "id": "default",
            "name": "Default User",
            "settings": {}
        })
    elif request.method == 'POST':
        return web.json_response({"status": "ok"})
    return web.json_response({"error": "Method not allowed"}, status=405)


async def handle_settings(request):
    """设置API"""
    if request.method == 'GET':
        return web.json_response({})
    elif request.method == 'POST':
        return web.Response(status=200)
    return web.json_response({"error": "Method not allowed"}, status=405)


async def handle_settings_item(request):
    """设置项API - /api/settings/{key}"""
    if request.method == 'GET':
        return web.json_response(None)
    elif request.method == 'POST':
        return web.Response(status=200)
    return web.json_response({"error": "Method not allowed"}, status=405)


async def handle_userdata(request):
    """用户数据API - 处理工作流和用户文件的存储"""
    try:
        # 获取参数（支持查询参数和路径参数）
        directory = request.rel_url.query.get('dir', '')
        file_param = request.rel_url.query.get('file', '')
        
        # 如果路径中包含文件路径（如 /userdata/workflows/signal.json）
        path_parts = request.match_info.get('path', '').strip('/')
        if path_parts:
            parts = path_parts.split('/')
            if len(parts) == 1:
                # 只有文件名
                file_param = parts[0] if not file_param else file_param
            elif len(parts) >= 2:
                # 目录 + 文件名
                directory = '/'.join(parts[:-1]) if not directory else directory
                file_param = parts[-1] if not file_param else file_param
        
        if request.method == 'GET':
            # 列出目录内容
            if directory:
                target_dir = USER_DIR / directory
                if target_dir.exists() and target_dir.is_dir():
                    files = []
                    for item in target_dir.iterdir():
                        if item.is_file():
                            files.append(item.name)
                    return web.json_response(files)
                else:
                    return web.json_response([])
            else:
                # 列出根目录
                dirs = []
                if USER_DIR.exists():
                    for item in USER_DIR.iterdir():
                        if item.is_dir():
                            dirs.append(item.name)
                return web.json_response(dirs)
        
        elif request.method == 'POST':
            # 保存文件（file_param 已在开头解析）
            if not file_param:
                return web.json_response({"error": "Missing file parameter"}, status=400)
            
            # 构建文件路径
            if directory:
                target_dir = USER_DIR / directory
                target_dir.mkdir(parents=True, exist_ok=True)
                file_path = target_dir / file_param
            else:
                file_path = USER_DIR / file_param
            
            # 安全检查
            try:
                file_path = file_path.resolve()
                USER_DIR.resolve()
                if not str(file_path).startswith(str(USER_DIR.resolve())):
                    return web.json_response({"error": "Invalid path"}, status=403)
            except:
                return web.json_response({"error": "Invalid path"}, status=403)
            
            # 读取请求体并保存
            content = await request.read()
            file_path.write_bytes(content)
            
            print(f"[OK] Saved user data: {file_path}")
            return web.json_response({"status": "ok"})
        
        elif request.method == 'DELETE':
            # 删除文件（file_param 已在开头解析）
            if not file_param:
                return web.json_response({"error": "Missing file parameter"}, status=400)
            
            # 构建文件路径
            if directory:
                file_path = USER_DIR / directory / file_param
            else:
                file_path = USER_DIR / file_param
            
            # 安全检查和删除
            try:
                file_path = file_path.resolve()
                if str(file_path).startswith(str(USER_DIR.resolve())) and file_path.exists():
                    file_path.unlink()
                    print(f"[OK] Deleted user data: {file_path}")
                    return web.json_response({"status": "ok"})
                else:
                    return web.json_response({"error": "File not found"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)
        
        else:
            return web.json_response({"error": "Method not allowed"}, status=405)
    
    except Exception as e:
        print(f"[X] Error in handle_userdata: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def handle_i18n(request):
    """国际化API - 返回中文翻译"""
    return web.json_response({
        "en": {
            "common": {
                "save": "Save",
                "load": "Load",
                "run": "Run",
                "clear": "Clear",
                "delete": "Delete"
            }
        },
        "zh": {
            "common": {
                "save": "保存",
                "load": "加载",
                "run": "运行",
                "clear": "清空",
                "delete": "删除"
            }
        }
    })


async def handle_user_css(request):
    """用户CSS文件"""
    return web.Response(text="", content_type="text/css")


async def handle_experiment_models(request):
    """实验模型API"""
    return web.json_response([])


async def handle_workflows(request):
    """工作流API"""
    return web.json_response([])


async def handle_entities(request):
    """实体API"""
    return web.json_response([])


async def handle_manifest(request):
    """Manifest文件API"""
    return web.json_response({
        "name": "ComfyUI",
        "short_name": "ComfyUI",
        "start_url": "/",
        "display": "standalone"
    })


# ==================== 图片查看API ====================

async def handle_view_image(request):
    """查看图片 - ComfyUI标准实现"""
    if "filename" not in request.rel_url.query:
        return web.Response(text="Missing filename parameter", status=400)
    
    filename = request.rel_url.query["filename"]
    
    # 安全检查
    if filename[0] == '/' or '..' in filename:
        return web.Response(status=400)
    
    # 确定目录
    type_param = request.rel_url.query.get("type", "output")
    if type_param == "output":
        output_dir = OUTPUT_DIR
    elif type_param == "input":
        output_dir = INPUT_DIR
    elif type_param == "temp":
        output_dir = TEMP_DIR
    else:
        output_dir = OUTPUT_DIR
    
    # 处理子文件夹
    if "subfolder" in request.rel_url.query:
        subfolder = request.rel_url.query["subfolder"]
        if subfolder:
            full_output_dir = output_dir / subfolder
            # 安全检查
            if not str(full_output_dir).startswith(str(output_dir)):
                return web.Response(status=403)
            output_dir = full_output_dir
    
    # 只取文件名
    filename = os.path.basename(filename)
    file_path = output_dir / filename
    
    if file_path.is_file():
        return web.FileResponse(file_path)
    else:
        print(f"[X] Image not found: {file_path}")
        return web.Response(status=404)


# ==================== 工作流执行引擎 ====================

async def execute_workflow(workflow_data: dict, prompt_id: str) -> dict:
    """
    执行工作流 - 完整实现
    使用拓扑排序确保正确的执行顺序
    """
    print("\n[>>] Executing workflow...")
    print(f"    Prompt ID: {prompt_id}")
    
    # 拓扑排序
    def topological_sort(nodes):
        """拓扑排序 - 根据节点依赖关系排序"""
        in_degree = {node_id: 0 for node_id in nodes}
        graph = {node_id: [] for node_id in nodes}
        
        # 构建依赖图
        for node_id, node_data in nodes.items():
            # 验证node_data是字典
            if not isinstance(node_data, dict):
                print(f"[X] Invalid node_data for node {node_id}: {type(node_data)}")
                print(f"    node_data content: {node_data}")
                continue
            
            inputs = node_data.get('inputs', {})
            for input_value in inputs.values():
                if isinstance(input_value, list) and len(input_value) >= 2:
                    source_node_id = input_value[0]
                    if source_node_id in nodes:
                        graph[source_node_id].append(node_id)
                        in_degree[node_id] += 1
        
        # 拓扑排序
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(nodes):
            print("[X] Warning: Circular dependency detected!")
        
        return result
    
    # 执行节点
    execution_order = topological_sort(workflow_data)
    print(f"    Execution order: {execution_order}")
    
    node_outputs = {}
    errors = {}
    
    for node_id in execution_order:
        node_data = workflow_data[node_id]
        class_type = node_data.get('class_type')
        inputs = node_data.get('inputs', {})
        
        print(f"\n[*] Executing node {node_id}: {class_type}")
        
        # 获取节点实例（先尝试基础节点，再尝试信号处理节点）
        node_instance = get_node_instance(class_type)
        if not node_instance and SIGNAL_NODES_AVAILABLE:
            node_instance = get_signal_node_instance(class_type)
        
        if not node_instance:
            print(f"    [X] Unknown node type: {class_type}")
            errors[node_id] = f"Unknown node type: {class_type}"
            continue
        
        # 准备输入数据
        node_inputs = {}
        for input_name, input_value in inputs.items():
            if isinstance(input_value, list) and len(input_value) >= 2:
                # 连接输入
                source_node_id = input_value[0]
                output_index = input_value[1] if len(input_value) > 1 else 0
                
                if source_node_id in node_outputs:
                    output_data = node_outputs[source_node_id]
                    
                    # 智能匹配输出数据
                    if input_name in ["image", "images"] and "IMAGE" in output_data:
                        node_inputs[input_name] = output_data["IMAGE"]
                    elif input_name == "samples" and "LATENT" in output_data:
                        node_inputs[input_name] = output_data["LATENT"]
                    elif input_name == "vae" and "VAE" in output_data:
                        node_inputs[input_name] = output_data["VAE"]
                    # 信号处理节点数据类型
                    elif input_name == "raw_data" and "RAW_DATA" in output_data:
                        node_inputs[input_name] = output_data["RAW_DATA"]
                    elif input_name == "frame" and "FRAME" in output_data:
                        node_inputs[input_name] = output_data["FRAME"]
                    elif input_name == "signal_data" and "SIGNAL_DATA" in output_data:
                        node_inputs[input_name] = output_data["SIGNAL_DATA"]
                    elif input_name == "buffer_stats" and "BUFFER_STATS" in output_data:
                        node_inputs[input_name] = output_data["BUFFER_STATS"]
                    else:
                        # 使用第一个可用的输出
                        values = list(output_data.values())
                        if values:
                            node_inputs[input_name] = values[0]
                else:
                    print(f"    [X] Source node {source_node_id} not found")
            else:
                # 直接值输入
                node_inputs[input_name] = input_value
        
        # 执行节点
        try:
            result = node_instance.execute(node_inputs, node_id)
            # 保留原始对象（如PIL Image）供后续节点使用
            node_outputs[node_id] = result if result else {}
            print(f"    [OK] Node {node_id} executed successfully")
        except Exception as e:
            print(f"    [X] Execution error: {e}")
            import traceback
            traceback.print_exc()
            errors[node_id] = str(e)
            node_outputs[node_id] = {}
    
    print("\n[OK] Workflow completed!\n")
    
    # 过滤结果 - 移除不可序列化的对象，保留ui信息
    serializable_outputs = {}
    for node_id, output in node_outputs.items():
        serializable_output = {}
        if isinstance(output, dict):
            for key, value in output.items():
                if key == "ui":
                    # ui信息必须保留
                    serializable_output[key] = value
                elif hasattr(value, 'save'):
                    # PIL Image对象不序列化
                    pass
                else:
                    # 其他可序列化数据
                    serializable_output[key] = value
        serializable_outputs[node_id] = serializable_output
    
    return {
        "status": "success",
        "node_outputs": serializable_outputs,
        "errors": errors
    }


# ==================== WebSocket处理 ====================

async def handle_websocket(request):
    """WebSocket处理 - 实时通信"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    websocket_clients.add(ws)
    print(f"[>>] WebSocket client connected (total: {len(websocket_clients)})")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                # 处理客户端消息
                try:
                    data = json.loads(msg.data)
                    print(f"[>>] WebSocket message received: {data.get('type', 'unknown')}")
                except:
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                print(f"[X] WebSocket error: {ws.exception()}")
    finally:
        websocket_clients.discard(ws)
        print(f"[>>] WebSocket client disconnected (total: {len(websocket_clients)})")
    
    return ws


async def broadcast_message(message: dict):
    """广播消息到所有WebSocket客户端"""
    if not websocket_clients:
        return
    
    message_str = json.dumps(message)
    for ws in websocket_clients.copy():
        try:
            await ws.send_str(message_str)
        except Exception as e:
            print(f"[X] WebSocket send error: {e}")
            websocket_clients.discard(ws)


# ==================== 服务器启动 ====================

async def start_server():
    """启动服务器"""
    print("\n" + "="*60)
    print("  Full-Featured ComfyUI Server")
    print("  完整功能ComfyUI服务器")
    print("="*60)
    
    # 获取前端路径
    frontend_path = get_frontend_path()
    if not frontend_path:
        print("\n[X] Cannot start without frontend package!")
        return
    
    print(f"\n[OK] Frontend: {frontend_path}")
    
    # 检查index.html
    index_file = Path(frontend_path) / "index.html"
    if not index_file.exists():
        print(f"[X] index.html not found at {index_file}")
        return
    
    print(f"[OK] Found: {index_file}")
    print(f"[OK] Basic nodes: {list(NODE_REGISTRY.keys())}")
    if SIGNAL_NODES_AVAILABLE:
        print(f"[OK] Signal nodes: {list(SIGNAL_NODE_REGISTRY.keys())}")
        print(f"[OK] Total nodes: {len(NODE_REGISTRY) + len(SIGNAL_NODE_REGISTRY)}")
    
    # 创建应用
    app = web.Application(middlewares=[cors_middleware])
    
    # 根路径处理
    async def handle_root(request):
        """处理根路径"""
        index_path = Path(frontend_path) / "index.html"
        return web.FileResponse(index_path)
    
    # ==================== 路由配置 ====================
    
    # WebSocket
    app.router.add_get('/ws', handle_websocket)
    
    # 核心API - 同时注册 /api/ 和无前缀版本
    app.router.add_post('/prompt', handle_prompt)
    app.router.add_post('/api/prompt', handle_prompt)
    
    app.router.add_get('/object_info', handle_object_info)
    app.router.add_get('/api/object_info', handle_object_info)
    
    app.router.add_get('/queue', handle_queue)
    app.router.add_get('/api/queue', handle_queue)
    
    app.router.add_get('/history', handle_history)
    app.router.add_get('/history/{prompt_id}', handle_history)
    app.router.add_get('/api/history', handle_history)
    app.router.add_get('/api/history/{prompt_id}', handle_history)
    
    app.router.add_get('/embeddings', handle_embeddings)
    app.router.add_get('/api/embeddings', handle_embeddings)
    
    app.router.add_get('/extensions', handle_extensions)
    app.router.add_get('/api/extensions', handle_extensions)
    
    app.router.add_get('/system_stats', handle_system_stats)
    app.router.add_get('/api/system_stats', handle_system_stats)
    
    # 用户相关API
    app.router.add_get('/users', handle_users)
    app.router.add_post('/users', handle_users)
    app.router.add_get('/api/users', handle_users)
    app.router.add_post('/api/users', handle_users)
    
    app.router.add_get('/users/{username}', handle_user_config)
    app.router.add_get('/api/users/{username}', handle_user_config)
    
    app.router.add_get('/user_config', handle_user_config)
    app.router.add_post('/user_config', handle_user_config)
    app.router.add_get('/api/user_config', handle_user_config)
    app.router.add_post('/api/user_config', handle_user_config)
    
    app.router.add_get('/settings', handle_settings)
    app.router.add_post('/settings', handle_settings)
    app.router.add_get('/api/settings', handle_settings)
    app.router.add_post('/api/settings', handle_settings)
    
    app.router.add_get('/settings/{key:.*}', handle_settings_item)
    app.router.add_post('/settings/{key:.*}', handle_settings_item)
    app.router.add_get('/api/settings/{key:.*}', handle_settings_item)
    app.router.add_post('/api/settings/{key:.*}', handle_settings_item)
    
    # 用户数据路由（支持查询参数和路径参数）
    app.router.add_get('/userdata', handle_userdata)
    app.router.add_post('/userdata', handle_userdata)
    app.router.add_delete('/userdata', handle_userdata)
    app.router.add_get('/userdata/{path:.*}', handle_userdata)
    app.router.add_post('/userdata/{path:.*}', handle_userdata)
    app.router.add_delete('/userdata/{path:.*}', handle_userdata)
    app.router.add_get('/api/userdata', handle_userdata)
    app.router.add_post('/api/userdata', handle_userdata)
    app.router.add_delete('/api/userdata', handle_userdata)
    app.router.add_get('/api/userdata/{path:.*}', handle_userdata)
    app.router.add_post('/api/userdata/{path:.*}', handle_userdata)
    app.router.add_delete('/api/userdata/{path:.*}', handle_userdata)
    
    # 其他API
    app.router.add_get('/api/i18n', handle_i18n)
    app.router.add_get('/api/experiment/models', handle_experiment_models)
    app.router.add_get('/api/workflows', handle_workflows)
    app.router.add_get('/api/entities', handle_entities)
    app.router.add_get('/manifest.json', handle_manifest)
    app.router.add_get('/user.css', handle_user_css)
    
    # 图片查看
    app.router.add_get('/view', handle_view_image)
    app.router.add_get('/api/view', handle_view_image)
    
    # 根路径
    app.router.add_get('/', handle_root)
    
    # 静态文件（最后添加）
    app.router.add_static('/', frontend_path, show_index=False, follow_symlinks=True)
    
    # ==================== 启动服务器 ====================
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8188)
    await site.start()
    
    print(f"\n[>>] Server running at: http://127.0.0.1:8188")
    print(f"[>>] Input dir: {INPUT_DIR.absolute()}")
    print(f"[>>] Output dir: {OUTPUT_DIR.absolute()}")
    print(f"[>>] Temp dir: {TEMP_DIR.absolute()}")
    print(f"[>>] User dir: {USER_DIR.absolute()}")
    print(f"\n[>>] Open browser and start creating!")
    print("Press Ctrl+C to stop\n")
    
    # 保持运行
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n[>>] Shutting down...")
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\n[OK] Server stopped")

