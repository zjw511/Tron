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
        """执行表格预览 - 生成表格图片"""
        import uuid
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # 非GUI后端
        
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
        
        # 限制显示行数
        display_rows = min(20, len(df))  # 最多显示20行
        df_display = df.head(display_rows)
        
        # 生成表格图片
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"table_{node_id}_{unique_id}.png"
        image_path = Path(self.output_dir) / image_filename
        
        try:
            # 计算合适的图片尺寸
            num_cols = len(df_display.columns)
            num_rows = len(df_display)
            
            # 根据列数和行数动态调整图片大小
            # 每列约1.2英寸，每行约0.35英寸
            col_width = min(1.5, max(0.8, 12 / (num_cols + 1)))  # 动态列宽
            fig_width = min(20, (num_cols + 1) * col_width)  # 最大20英寸宽
            fig_height = min(15, num_rows * 0.35 + 1.5)  # 最大15英寸高
            
            # 创建图表，去除所有边距
            fig = plt.figure(figsize=(fig_width, fig_height))
            fig.patch.set_facecolor('#1e1e1e')
            
            # 添加标题（在figure上）
            fig.suptitle(
                f"{title}  |  {len(df)} rows × {len(df.columns)} columns" + 
                (f"  (showing first {display_rows})" if len(df) > display_rows else ""),
                color='white', fontsize=11, y=0.98
            )
            
            # 创建ax，占据几乎全部空间
            ax = fig.add_subplot(111)
            ax.axis('tight')
            ax.axis('off')
            
            # 准备表格数据（格式化显示）
            cell_text = []
            for row in df_display.values:
                formatted_row = []
                for cell in row:
                    if pd.isna(cell):
                        formatted_row.append('NaN')
                    elif isinstance(cell, float):
                        formatted_row.append(f'{cell:.4f}' if abs(cell) < 1000 else f'{cell:.2e}')
                    else:
                        # 限制单元格文本长度
                        cell_str = str(cell)
                        formatted_row.append(cell_str[:50] + '...' if len(cell_str) > 50 else cell_str)
                cell_text.append(formatted_row)
            
            col_labels = list(df_display.columns)
            row_labels = [str(i) for i in range(len(df_display))]
            
            # 创建表格
            table = ax.table(
                cellText=cell_text,
                rowLabels=row_labels,
                colLabels=col_labels,
                cellLoc='left',
                loc='center',
                colWidths=[col_width / fig_width] * num_cols  # 均匀分配宽度
            )
            
            # 设置样式
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.2)  # 减小垂直缩放，更紧凑
            
            # 设置颜色
            for (i, j), cell in table.get_celld().items():
                if i == 0:  # 表头
                    cell.set_facecolor('#2a2a2a')
                    cell.set_text_props(color='white', weight='bold', fontsize=8)
                elif j == -1:  # 行号列
                    cell.set_facecolor('#2a2a2a')
                    cell.set_text_props(color='#888', fontsize=7, ha='center')
                else:  # 数据单元格
                    if i % 2 == 0:
                        cell.set_facecolor('#1a1a1a')
                    else:
                        cell.set_facecolor('#242424')
                    cell.set_text_props(color='#ddd', fontsize=8)
                
                cell.set_edgecolor('#444')
                cell.set_linewidth(0.5)
                
                # 减少padding
                cell.PAD = 0.02
            
            # 调整布局，减少边距
            plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02)
            
            # 保存图片，去除多余空白
            plt.savefig(
                image_path, 
                facecolor='#1e1e1e', 
                dpi=120,  # 提高清晰度
                bbox_inches='tight',
                pad_inches=0.1  # 最小边距
            )
            plt.close()
            
            print(f"    [OK] Preview table: {df.shape[0]} rows × {df.shape[1]} cols")
            print(f"    [OK] Saved table image: {image_filename}")
            
            # 返回图片（像PreviewImage一样）
            return {
                "ui": {
                    "images": [{
                        "filename": image_filename,
                        "subfolder": "",
                        "type": "temp"
                    }]
                }
            }
            
        except Exception as e:
            print(f"    [X] Error generating table image: {e}")
            import traceback
            traceback.print_exc()
            return {"ui": {"text": [f"Error: {str(e)}"]}}
    
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

