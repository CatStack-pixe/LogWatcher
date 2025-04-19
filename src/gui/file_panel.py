import tkinter as tk
from pathlib import Path
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import filedialog
import datetime

def init_dnd():
    """初始化拖放支持"""
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        # 测试 tkdnd 命令是否可用
        test_root = tk.Tk()
        try:
            test_root.tk.call('package', 'require', 'tkdnd')
            test_root.destroy()
            return True, DND_FILES, TkinterDnD
        except tk.TclError:
            test_root.destroy()
            return False, None, None
    except (ImportError, tk.TclError):
        return False, None, None

# 全局初始化拖放
DND_AVAILABLE, DND_FILES, TkinterDnD = init_dnd()

from src.utils.tooltip import ToolTip

class FilePanel:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.current_dir = None
        self._create_widgets()
        
    def _create_widgets(self):
        """创建文件面板组件"""
        toolbar = ttkb.Frame(self.parent)
        ttkb.Button(toolbar, text="打开目录", command=self.load_directory, 
                   bootstyle="primary").pack(side="left", padx=2, pady=2)
        ttkb.Button(toolbar, text="刷新", command=self.refresh_files, 
                   bootstyle="secondary").pack(side="left", padx=2, pady=2)
        ttkb.Button(toolbar, text="批量处理", command=self.app.batch_process, 
                   bootstyle="success").pack(side="left", padx=2, pady=2)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        # 添加搜索框
        search_frame = ttkb.Frame(self.parent)
        search_frame.pack(fill="x", padx=5, pady=2)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_files)
        ttkb.Entry(search_frame, textvariable=self.search_var).pack(fill="x", expand=True)
        
        # 文件列表区域
        list_frame = ttkb.Frame(self.parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.file_list = tk.Listbox(list_frame, selectmode="extended",
                                   bg="white", fg="#333333",
                                   font=("Segoe UI", 10),
                                   relief="solid")
        scrollbar = ttkb.Scrollbar(list_frame, orient="vertical",
                                 command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 尝试启用拖放功能
        if DND_AVAILABLE:
            try:
                self.file_list.drop_target_register(DND_FILES)
                self.file_list.dnd_bind('<<Drop>>', self._on_drop)
            except (tk.TclError, AttributeError) as e:
                print(f"注意: 拖放功能初始化失败 - {e}")
        
        # 绑定文件选择事件
        self.file_list.bind('<<ListboxSelect>>', self.app.on_file_select)
        self.file_list.bind('<Double-Button-1>', self._on_double_click)
        
    def _on_drop(self, event):
        """处理文件拖放事件"""
        if not DND_AVAILABLE:
            return
            
        try:
            # 解析拖放的文件路径
            files = event.widget.tk.splitlist(event.data)
            if files:
                path = Path(files[0])
                if path.is_dir():
                    self.current_dir = path
                    self.refresh_files()
                elif path.is_file():
                    self.current_dir = path.parent
                    self.refresh_files()
                    # 选中拖放的文件
                    try:
                        idx = self.file_list.get(0, "end").index(path.name)
                        self.file_list.selection_clear(0, "end")
                        self.file_list.selection_set(idx)
                        self.app.on_file_select(None)
                    except ValueError:
                        pass
        except Exception as e:
            print(f"处理拖放事件时出错: {e}")

    def _on_double_click(self, event):
        """处理双击事件"""
        selection = self.file_list.curselection()
        if selection:
            index = selection[0]
            filename = self.file_list.get(index)
            path = self.current_dir / filename
            if path.is_dir():
                self.current_dir = path
                self.refresh_files()

    def load_directory(self):
        """加载目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.current_dir = Path(directory)
            self.refresh_files()
            
    def refresh_files(self):
        """刷新文件列表"""
        if not self.current_dir:
            return
            
        self.file_list.delete(0, "end")
        
        try:
            # 添加返回上级目录选项
            if self.current_dir.parent != self.current_dir:
                self.file_list.insert("end", "..")
            
            # 添加子目录
            for item in sorted(self.current_dir.iterdir()):
                if item.is_dir():
                    self.file_list.insert("end", f"📁 {item.name}")
                elif item.suffix.lower() in ['.log', '.txt']:
                    self.file_list.insert("end", item.name)
                    
        except Exception as e:
            self.app.log_error(f"刷新文件列表失败: {e}")
            
    def filter_files(self, *args):
        """根据搜索条件过滤文件列表"""
        if not self.current_dir:
            return
            
        search_text = self.search_var.get().lower()
        self.file_list.delete(0, "end")
        
        try:
            # 添加返回上级目录选项
            if self.current_dir.parent != self.current_dir:
                self.file_list.insert("end", "..")
            
            # 过滤并添加文件
            for item in sorted(self.current_dir.iterdir()):
                if search_text in item.name.lower():
                    if item.is_dir():
                        self.file_list.insert("end", f"📁 {item.name}")
                    elif item.suffix.lower() in ['.log', '.txt']:
                        self.file_list.insert("end", item.name)
                        
        except Exception as e:
            self.app.log_error(f"过滤文件列表失败: {e}")
            
    def get_selected_files(self) -> list[Path]:
        """获取选中的文件列表"""
        selection = self.file_list.curselection()
        files = []
        
        for index in selection:
            filename = self.file_list.get(index)
            # 跳过目录和返回上级选项
            if not filename.startswith("📁") and filename != "..":
                path = self.current_dir / filename
                if path.is_file():
                    files.append(path)
                    
        return files