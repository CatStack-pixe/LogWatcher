import tkinter as tk
from pathlib import Path
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import filedialog
import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD

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
        search_entry = ttkb.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        ttkb.Label(search_frame, text="🔍", bootstyle="secondary").pack(side="right", padx=5)
        
        # 创建文件列表
        self.file_list = ttkb.Treeview(self.parent, 
                                      columns=("size", "modified"), 
                                      selectmode="extended")
        self.file_list.heading("#0", text="文件名")
        self.file_list.heading("size", text="大小")
        self.file_list.heading("modified", text="修改时间")
        self.file_list.column("size", width=80, anchor="e")
        self.file_list.column("modified", width=150, anchor="w")
        
        # 添加滚动条
        vsb = ttkb.Scrollbar(self.parent, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=vsb.set)
        
        # 布局
        self.file_list.pack(side="left", fill="both", expand=True, padx=(5,0), pady=5)
        vsb.pack(side="right", fill="y", padx=(0,5), pady=5)
        
        # 绑定事件
        self.file_list.bind("<<TreeviewSelect>>", self.app.on_file_select)
        self.file_list.drop_target_register(DND_FILES)
        self.file_list.dnd_bind('<<Drop>>', self._on_drop)

    def load_directory(self):
        """打开目录选择对话框并加载指定目录中的日志文件"""
        dir_path = filedialog.askdirectory(
            title="选择日志文件目录",
            initialdir=self.current_dir if self.current_dir else Path.cwd()
        )
        
        if dir_path:
            try:
                self.current_dir = Path(dir_path)
                self.refresh_files()
                self.app.log_info(f"已加载目录：{self.current_dir}")
            except Exception as e:
                self.app.log_error(f"加载目录失败：{e}")

    def refresh_files(self):
        """刷新文件列表"""
        self.search_var.set("")  # 清空搜索框
        self.file_list.delete(*self.file_list.get_children())
        if not self.current_dir:
            return
            
        try:
            files = sorted([p for p in self.current_dir.iterdir() 
                          if p.is_file() and p.suffix.lower() in {'.log', '.txt'}])
            for f in files:
                size = f.stat().st_size // 1024
                modified = f.stat().st_mtime
                modified_time = datetime.datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M')
                self.file_list.insert("", "end", iid=f.name, text=f.name,
                                    values=(f"{size} KB", modified_time))
            
            # 通知应用更新系统信息
            self.app._update_system_info()
            
        except Exception as e:
            self.app.log_error(f"读取目录出错: {e}")

    def filter_files(self, *args):
        """根据搜索框内容过滤文件列表"""
        search_term = self.search_var.get().lower()
        
        # 清空当前列表
        self.file_list.delete(*self.file_list.get_children())
        
        if not self.current_dir:
            return
            
        try:
            # 获取所有文件并按名称排序
            files = sorted([p for p in self.current_dir.iterdir() 
                          if p.is_file() and p.suffix.lower() in {'.log', '.txt'}])
            
            # 应用过滤
            for f in files:
                if search_term in f.name.lower():
                    size = f.stat().st_size // 1024
                    modified = f.stat().st_mtime
                    modified_time = datetime.datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M')
                    self.file_list.insert("", "end", iid=f.name, text=f.name,
                                        values=(f"{size} KB", modified_time))
                                        
            # 更新系统信息显示
            total_files = len(files)
            filtered_files = len(self.file_list.get_children())
            info = [
                f"文件统计信息:",
                f"总文件数: {total_files}",
                f"显示文件数: {filtered_files}",
                f"过滤条件: {search_term if search_term else '无'}"
            ]
            self.app.update_system_info("\n".join(info))
                
        except Exception as e:
            self.app.log_error(f"过滤文件时出错: {e}")

    def get_selected_files(self):
        """获取选中的文件列表"""
        return [self.current_dir / name for name in self.file_list.selection()]

    def _on_drop(self, event):
        """处理文件拖放"""
        try:
            # 获取拖放的文件路径
            file_paths = event.data.split(' ')  # tkinterdnd2以空格分隔多个文件
            if not file_paths:
                return
                
            # 处理Windows特殊字符
            file_paths = [path.strip('{}') for path in file_paths]
                
            # 如果是单个目录，设置为当前目录
            first_path = Path(file_paths[0])
            if len(file_paths) == 1 and first_path.is_dir():
                self.current_dir = first_path
                self.refresh_files()
                self.app.log_info(f"已加载目录：{self.current_dir}")
                return
                
            # 如果是文件，确保它们都在同一个目录下
            if not first_path.parent.exists():
                self.app.log_error("无效的文件路径")
                return
                
            # 设置当前目录为第一个文件的目录
            self.current_dir = first_path.parent
            self.refresh_files()
            
            # 选中拖放的文件
            valid_files = [Path(f) for f in file_paths 
                         if Path(f).suffix.lower() in {'.log', '.txt'}]
            
            if not valid_files:
                self.app.log_error("没有找到有效的日志文件")
                return
                
            # 清除现有选择
            self.file_list.selection_set('')
            
            # 选中有效的文件
            for file_path in valid_files:
                if self.file_list.exists(file_path.name):
                    self.file_list.selection_add(file_path.name)
            
            self.app.log_info(f"已添加 {len(valid_files)} 个文件")
            
            # 如果有选中的文件，更新预览
            if valid_files and self.app.config_panel.live_preview.get():
                self.app.current_file = valid_files[0]
                self.app.preview_filtered()
            
        except Exception as e:
            self.app.log_error(f"处理拖放文件时出错: {e}")