"""
节点模块 - 模块化节点定义
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from PIL import Image
import os


class NodeBase(ABC):
    """节点基类"""
    
    def __init__(self):
        self.name = ""
        self.category = ""
        self.icon = ""
        self.inputs = []
        self.outputs = []
        self.description = ""
    
    @abstractmethod
    def get_node_info(self) -> Dict[str, Any]:
        """获取节点信息"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行节点逻辑"""
        pass


class LoadImageNode(NodeBase):
    """加载图片节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "LoadImage"
        self.category = "image"
        self.icon = "🖼️"
        self.inputs = []
        self.outputs = ["IMAGE"]
        self.description = "Load an image file"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "image": ["STRING", {"image_upload": True}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "LoadImage",
            "display_name": "Load Image",
            "description": "Load an image file",
            "category": "image",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行加载图片"""
        image_name = inputs.get("image", "test.png")
        image_path = f"input/{image_name}"
        
        if os.path.exists(image_path):
            img = Image.open(image_path)
            print(f"    [OK] Loaded: {image_path} ({img.size})")
            return {"IMAGE": img}
        else:
            print(f"    [X] Not found: {image_path}")
            return {}


class SaveImageNode(NodeBase):
    """保存图片节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "SaveImage"
        self.category = "image"
        self.icon = "💾"
        self.inputs = ["IMAGE"]
        self.outputs = []
        self.description = "Save the image"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "images": ["IMAGE", {}],
                    "filename_prefix": ["STRING", {"default": "ComfyUI"}]
                }
            },
            "output": [],
            "output_is_list": [],
            "output_name": [],
            "name": "SaveImage",
            "display_name": "Save Image",
            "description": "Save the image",
            "category": "image",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行保存图片"""
        filename = inputs.get("filename_prefix", "ComfyUI")
        images = inputs.get("images")
        
        if images:
            output_path = f"output/{filename}.png"
            images.save(output_path)
            print(f"    [OK] Saved: {output_path}")
            return {"status": "saved"}
        else:
            print(f"    [X] No image to save")
            return {}


class ImageScaleNode(NodeBase):
    """图片缩放节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "ImageScale"
        self.category = "image"
        self.icon = "🔍"
        self.inputs = ["IMAGE"]
        self.outputs = ["IMAGE"]
        self.description = "Scale the image"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "image": ["IMAGE", {}],
                    "upscale_method": [["nearest-exact", "bilinear", "area", "bicubic", "lanczos"], {}],
                    "width": ["INT", {"default": 512, "min": 1, "max": 8192, "step": 1}],
                    "height": ["INT", {"default": 512, "min": 1, "max": 8192, "step": 1}],
                    "crop": [["disabled", "center"], {}]
                }
            },
            "output": ["IMAGE"],
            "output_is_list": [False],
            "output_name": ["IMAGE"],
            "name": "ImageScale",
            "display_name": "Upscale Image",
            "description": "Upscale the image",
            "category": "image/upscaling",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行图片缩放"""
        image = inputs.get("image")
        width = inputs.get("width", 512)
        height = inputs.get("height", 512)
        
        if image:
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            print(f"    [OK] Resized to {width}x{height}")
            return {"IMAGE": resized}
        else:
            print(f"    [X] No image to resize")
            return {}


class PreviewImageNode(NodeBase):
    """预览图片节点 - 完全照抄ComfyUI原版SaveImage逻辑"""
    
    def __init__(self):
        super().__init__()
        self.name = "PreviewImage"
        self.category = "image"
        self.icon = "👁️"
        self.inputs = ["IMAGE"]
        self.outputs = []
        self.description = "Preview images"
        # 照抄ComfyUI原版PreviewImage设置
        self.output_dir = "temp"
        self.type = "temp"
        self.compress_level = 1
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "images": ["IMAGE", {}]
                }
            },
            "output": [],
            "output_is_list": [],
            "output_name": [],
            "name": "PreviewImage",
            "display_name": "Preview Image",
            "description": "Preview images",
            "category": "image",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行预览图片 - 完全照抄ComfyUI原版save_images逻辑"""
        import random
        import string
        from pathlib import Path
        
        images = inputs.get("images")
        
        if not images:
            print(f"    [X] No image to preview")
            return {}
        
        # 提取PIL Image对象
        pil_image = None
        if hasattr(images, 'save'):
            pil_image = images
        elif isinstance(images, dict) and "IMAGE" in images:
            pil_image = images["IMAGE"]
        elif isinstance(images, dict):
            values = list(images.values())
            if values and hasattr(values[0], 'save'):
                pil_image = values[0]
        
        if not pil_image or not hasattr(pil_image, 'save'):
            print(f"    [X] Cannot find valid PIL Image object")
            return {}
        
        # 确保temp目录存在
        temp_dir = Path(self.output_dir)
        temp_dir.mkdir(exist_ok=True)
        
        # 照抄ComfyUI原版：生成文件名
        # ComfyUI使用: filename_prefix + "_temp_" + random + "_00001_.png"
        random_suffix = ''.join(random.choice("abcdefghijklmnopqrstupvxyz") for _ in range(5))
        filename_prefix = f"ComfyUI_temp_{random_suffix}"
        counter = 1
        filename = f"{filename_prefix}_{counter:05}_.png"
        
        # 保存图片
        file_path = temp_dir / filename
        pil_image.save(str(file_path), compress_level=self.compress_level)
        
        print(f"    [OK] Preview saved: {file_path} (size: {pil_image.size})")
        
        # 照抄ComfyUI原版：返回格式
        results = [{
            "filename": filename,
            "subfolder": "",
            "type": self.type
        }]
        
        return {"ui": {"images": results}}


class PrimitiveFloatNode(NodeBase):
    """浮点数节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "PrimitiveFloat"
        self.category = "primitives"
        self.icon = "🔢"
        self.inputs = []
        self.outputs = ["FLOAT"]
        self.description = "A float primitive"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "value": ["FLOAT", {"default": 0.0, "min": -3.4e38, "max": 3.4e38, "step": 0.01}]
                }
            },
            "output": ["FLOAT"],
            "output_is_list": [False],
            "output_name": ["FLOAT"],
            "name": "PrimitiveFloat",
            "display_name": "Float",
            "description": "A float primitive",
            "category": "primitives",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行浮点数"""
        value = inputs.get("value", 0.0)
        print(f"    [OK] Float value: {value}")
        return {"FLOAT": value}


class PrimitiveStringNode(NodeBase):
    """字符串节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "PrimitiveString"
        self.category = "primitives"
        self.icon = "📝"
        self.inputs = []
        self.outputs = ["STRING"]
        self.description = "A string primitive"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "string": ["STRING", {"default": ""}]
                }
            },
            "output": ["STRING"],
            "output_is_list": [False],
            "output_name": ["STRING"],
            "name": "PrimitiveString",
            "display_name": "String",
            "description": "A string primitive",
            "category": "primitives",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行字符串"""
        value = inputs.get("string", "")
        print(f"    [OK] String value: {value}")
        return {"STRING": value}


# 节点注册表
NODE_REGISTRY = {
    "LoadImage": LoadImageNode,
    "SaveImage": SaveImageNode,
    "ImageScale": ImageScaleNode,
    "PreviewImage": PreviewImageNode,
    "PrimitiveFloat": PrimitiveFloatNode,
    "PrimitiveString": PrimitiveStringNode,
}


def get_node_instance(node_type: str) -> Optional[NodeBase]:
    """获取节点实例"""
    if node_type in NODE_REGISTRY:
        return NODE_REGISTRY[node_type]()
    return None


def get_all_node_info() -> Dict[str, Any]:
    """获取所有节点信息"""
    result = {}
    for node_type, node_class in NODE_REGISTRY.items():
        instance = node_class()
        result[node_type] = instance.get_node_info()
    return result


# 节点模板 - 复制这个模板来创建新节点
"""
class YourNode(NodeBase):
    def __init__(self):
        super().__init__()
        self.name = "YourNode"
        self.category = "your_category"
        self.icon = "🔧"
        self.inputs = ["INPUT_TYPE"]
        self.outputs = ["OUTPUT_TYPE"]
        self.description = "Your node description"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "input_name": ["INPUT_TYPE", {"default": "default_value"}]
                }
            },
            "output": ["OUTPUT_TYPE"],
            "output_is_list": [False],
            "output_name": ["OUTPUT_TYPE"],
            "name": "YourNode",
            "display_name": "Your Node",
            "description": "Your node description",
            "category": "your_category",
            "output_node": False
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        # 获取输入
        input_value = inputs.get("input_name")
        
        # 处理逻辑
        result = your_processing_logic(input_value)
        
        # 返回输出
        return {"OUTPUT_TYPE": result}

# 记得在NODE_REGISTRY中注册新节点
# NODE_REGISTRY["YourNode"] = YourNode
"""
