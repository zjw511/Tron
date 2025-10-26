"""
表格数据显示节点
支持Excel、CSV、DataFrame等格式，在前端以表格形式显示
"""
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from nodes import NodeBase


class PreviewTableNode(NodeBase):
    """预览表格数据节点 - 在前端显示为交互式表格"""
    
    def __init__(self):
        super().__init__()
        self.name = "PreviewTable"
        self.category = "data"
        self.icon = "📊"
        self.inputs = ["TABLE_DATA"]
        self.outputs = []
        self.description = "Preview table data in frontend"
        self.output_dir = "temp"
        self.type = "temp"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "table_data": ["TABLE_DATA", {}]
                },
                "optional": {
                    "max_rows": ["INT", {"default": 100, "min": 10, "max": 10000}],
                    "title": ["STRING", {"default": "Data Table"}]
                }
            },
            "output": [],
            "output_is_list": [],
            "output_name": [],
            "name": "PreviewTable",
            "display_name": "Preview Table",
            "description": "Preview table data as interactive table",
            "category": "data",
            "output_node": True
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """执行表格预览"""
        import uuid
        
        table_data = inputs.get("table_data")
        max_rows = inputs.get("max_rows", 100)
        title = inputs.get("title", "Data Table")
        
        if table_data is None:
            print(f"    [X] No table data to preview")
            return {"ui": {"text": ["No data"]}}
        
        # 转换为DataFrame
        df = self._to_dataframe(table_data)
        
        if df is None or df.empty:
            print(f"    [X] Invalid or empty table data")
            return {"ui": {"text": ["Empty data"]}}
        
        # 限制行数
        if len(df) > max_rows:
            df = df.head(max_rows)
            truncated = True
        else:
            truncated = False
        
        # 转换为JSON格式
        table_json = {
            "id": str(uuid.uuid4()),
            "title": title,
            "columns": list(df.columns),
            "data": df.values.tolist(),
            "shape": df.shape,
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "truncated": truncated,
            "total_rows": len(df)
        }
        
        # 保存到文件（可选）
        output_path = Path(self.output_dir) / f"table_{table_json['id']}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(table_json, f, ensure_ascii=False, indent=2)
        
        print(f"    [OK] Preview table: {df.shape[0]} rows × {df.shape[1]} cols")
        if truncated:
            print(f"    [!] Showing first {max_rows} rows")
        
        # 返回给前端的数据
        return {
            "ui": {
                "table": [table_json]
            }
        }
    
    def _to_dataframe(self, data) -> pd.DataFrame:
        """将各种格式转换为DataFrame"""
        try:
            # Tuple格式（ComfyUI标准输出格式）
            if isinstance(data, tuple):
                if len(data) > 0:
                    # 递归处理tuple中的第一个元素
                    return self._to_dataframe(data[0])
                else:
                    return pd.DataFrame()
            
            # 已经是DataFrame
            if isinstance(data, pd.DataFrame):
                return data
            
            # 字典格式
            elif isinstance(data, dict):
                return pd.DataFrame(data)
            
            # 列表格式
            elif isinstance(data, list):
                if not data:
                    return pd.DataFrame()
                
                # 列表的列表
                if isinstance(data[0], (list, tuple)):
                    return pd.DataFrame(data)
                
                # 字典的列表
                elif isinstance(data[0], dict):
                    return pd.DataFrame(data)
                
                # 简单列表
                else:
                    return pd.DataFrame({"value": data})
            
            # NumPy数组
            elif hasattr(data, 'shape'):
                return pd.DataFrame(data)
            
            else:
                print(f"    [X] Unsupported data type: {type(data)}")
                return None
                
        except Exception as e:
            print(f"    [X] Error converting to DataFrame: {e}")
            return None


class LoadCSVNode(NodeBase):
    """加载CSV文件节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "LoadCSV"
        self.category = "data"
        self.icon = "📄"
        self.inputs = []
        self.outputs = ["TABLE_DATA"]
        self.description = "Load CSV file"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "file_path": ["STRING", {"default": "data.csv"}],
                },
                "optional": {
                    "encoding": ["STRING", {"default": "utf-8"}],
                    "separator": ["STRING", {"default": ","}]
                }
            },
            "output": ["TABLE_DATA"],
            "output_is_list": [False],
            "output_name": ["table_data"],
            "name": "LoadCSV",
            "display_name": "Load CSV",
            "description": "Load CSV file as table data",
            "category": "data"
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """加载CSV文件"""
        file_path = inputs.get("file_path", "data.csv")
        encoding = inputs.get("encoding", "utf-8")
        separator = inputs.get("separator", ",")
        
        try:
            df = pd.read_csv(file_path, encoding=encoding, sep=separator)
            print(f"    [OK] Loaded CSV: {df.shape[0]} rows × {df.shape[1]} cols")
            
            return {
                "result": (df,),
                "ui": {"text": [f"Loaded: {file_path}"]}
            }
            
        except Exception as e:
            print(f"    [X] Error loading CSV: {e}")
            return {
                "result": (None,),
                "ui": {"text": [f"Error: {str(e)}"]}
            }


class LoadExcelNode(NodeBase):
    """加载Excel文件节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "LoadExcel"
        self.category = "data"
        self.icon = "📊"
        self.inputs = []
        self.outputs = ["TABLE_DATA"]
        self.description = "Load Excel file"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "file_path": ["STRING", {"default": "data.xlsx"}],
                },
                "optional": {
                    "sheet_name": ["STRING", {"default": "0"}]
                }
            },
            "output": ["TABLE_DATA"],
            "output_is_list": [False],
            "output_name": ["table_data"],
            "name": "LoadExcel",
            "display_name": "Load Excel",
            "description": "Load Excel file as table data",
            "category": "data"
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """加载Excel文件"""
        file_path = inputs.get("file_path", "data.xlsx")
        sheet_name = inputs.get("sheet_name", "0")
        
        # 尝试转换为整数
        try:
            sheet_name = int(sheet_name)
        except:
            pass
        
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"    [OK] Loaded Excel: {df.shape[0]} rows × {df.shape[1]} cols")
            
            return {
                "result": (df,),
                "ui": {"text": [f"Loaded: {file_path}"]}
            }
            
        except Exception as e:
            print(f"    [X] Error loading Excel: {e}")
            return {
                "result": (None,),
                "ui": {"text": [f"Error: {str(e)}"]}
            }


class DataFrameToTableNode(NodeBase):
    """将任意数据转换为表格数据节点"""
    
    def __init__(self):
        super().__init__()
        self.name = "DataFrameToTable"
        self.category = "data"
        self.icon = "🔄"
        self.inputs = ["*"]
        self.outputs = ["TABLE_DATA"]
        self.description = "Convert data to table format"
    
    def get_node_info(self) -> Dict[str, Any]:
        return {
            "input": {
                "required": {
                    "data": ["*", {}]
                }
            },
            "output": ["TABLE_DATA"],
            "output_is_list": [False],
            "output_name": ["table_data"],
            "name": "DataFrameToTable",
            "display_name": "Convert to Table",
            "description": "Convert any data to table format",
            "category": "data"
        }
    
    def execute(self, inputs: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """转换数据为表格"""
        data = inputs.get("data")
        
        try:
            # 尝试转换为DataFrame
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, (dict, list)):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame({"value": [data]})
            
            print(f"    [OK] Converted to table: {df.shape[0]} rows × {df.shape[1]} cols")
            
            return {"result": (df,)}
            
        except Exception as e:
            print(f"    [X] Error converting to table: {e}")
            return {"result": (None,)}


# 节点注册
NODE_CLASS_MAPPINGS = {
    "PreviewTable": PreviewTableNode,
    "LoadCSV": LoadCSVNode,
    "LoadExcel": LoadExcelNode,
    "DataFrameToTable": DataFrameToTableNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PreviewTable": "Preview Table 📊",
    "LoadCSV": "Load CSV 📄",
    "LoadExcel": "Load Excel 📊",
    "DataFrameToTable": "Convert to Table 🔄",
}

