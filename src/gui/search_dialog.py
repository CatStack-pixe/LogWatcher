import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

class SearchDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = ttkb.Toplevel(parent)
        self.dialog.title("高级搜索")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        
        self.result = None
        self._create_widgets()
        
        # 设置模态
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
    def _create_widgets(self):
        """创建搜索对话框组件"""
        # 搜索条件框架
        search_frame = ttkb.Labelframe(self.dialog, text="搜索条件", padding=10)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        # 搜索文本
        ttkb.Label(search_frame, text="搜索文本:").grid(row=0, column=0, sticky="w", pady=5)
        self.search_text = ttkb.Entry(search_frame)
        self.search_text.grid(row=0, column=1, sticky="ew", padx=5)
        
        # 大小写敏感
        self.case_sensitive = ttkb.BooleanVar()
        ttkb.Checkbutton(search_frame, text="区分大小写",
                        variable=self.case_sensitive).grid(row=1, column=0,
                        columnspan=2, sticky="w", pady=5)
        
        # 使用正则表达式
        self.use_regex = ttkb.BooleanVar()
        ttkb.Checkbutton(search_frame, text="使用正则表达式",
                        variable=self.use_regex).grid(row=2, column=0,
                        columnspan=2, sticky="w", pady=5)
        
        # 搜索范围
        range_frame = ttkb.Labelframe(self.dialog, text="搜索范围", padding=10)
        range_frame.pack(fill="x", padx=10, pady=5)
        
        self.search_range = ttkb.StringVar(value="current")
        ttkb.Radiobutton(range_frame, text="当前文件",
                        variable=self.search_range,
                        value="current").pack(anchor="w", pady=2)
        ttkb.Radiobutton(range_frame, text="选中的文件",
                        variable=self.search_range,
                        value="selected").pack(anchor="w", pady=2)
        ttkb.Radiobutton(range_frame, text="所有文件",
                        variable=self.search_range,
                        value="all").pack(anchor="w", pady=2)
        
        # 按钮区域
        button_frame = ttkb.Frame(self.dialog)
        button_frame.pack(side="bottom", pady=10)
        
        ttkb.Button(button_frame, text="开始搜索",
                   command=self._on_search,
                   bootstyle="primary").pack(side="left", padx=5)
        ttkb.Button(button_frame, text="取消",
                   command=self._on_cancel,
                   bootstyle="secondary").pack(side="left", padx=5)
                   
        # 配置网格列权重
        search_frame.columnconfigure(1, weight=1)
        
        # 绑定回车键
        self.dialog.bind("<Return>", lambda e: self._on_search())
        self.dialog.bind("<Escape>", lambda e: self._on_cancel())
        
    def _on_search(self):
        """搜索按钮点击处理"""
        self.result = {
            'text': self.search_text.get(),
            'case_sensitive': self.case_sensitive.get(),
            'use_regex': self.use_regex.get(),
            'range': self.search_range.get()
        }
        self.dialog.destroy()
        
    def _on_cancel(self):
        """取消按钮点击处理"""
        self.dialog.destroy()
        
    @staticmethod
    def show_dialog(parent):
        """显示搜索对话框"""
        dialog = SearchDialog(parent)
        dialog.dialog.wait_window()
        return dialog.result