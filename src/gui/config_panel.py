import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from src.utils.tooltip import ToolTip

class ConfigPanel:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self._create_widgets()

    def _create_widgets(self):
        """创建配置面板组件"""
        config_frame = ttkb.Labelframe(self.parent, text="过滤配置", bootstyle="primary")
        
        # 关键字输入框
        keyword_frame = ttkb.Frame(config_frame)
        keyword_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        ttkb.Label(keyword_frame, text="关键字:").pack(side="left")
        self.keyword = ttkb.Entry(keyword_frame)
        self.keyword.insert(0, "[CHAT]")
        self.keyword.pack(side="left", fill="x", expand=True, padx=(5,0))
        ttkb.Label(keyword_frame, text="(用 | 分隔多个关键字)").pack(side="left", padx=(5,0))
        
        # 绑定关键词变化事件
        self.keyword_var = tk.StringVar()
        self.keyword.config(textvariable=self.keyword_var)
        self.keyword_var.trace_add("write", self._on_filter_change)
        
        # 过滤字段输入框
        filter_frame = ttkb.Frame(config_frame)
        filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        ttkb.Label(filter_frame, text="删除字段:").pack(side="left")
        self.filter_fields = ttkb.Entry(filter_frame)
        self.filter_fields.insert(0, "[Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]:")
        self.filter_fields.pack(side="left", fill="x", expand=True, padx=(5,0))
        ttkb.Label(filter_frame, text="(用 | 分隔多个字段)").pack(side="left", padx=(5,0))
        
        # 绑定过滤字段变化事件
        self.filter_var = tk.StringVar()
        self.filter_fields.config(textvariable=self.filter_var)
        self.filter_var.trace_add("write", self._on_filter_change)
        
        # 选项区域
        options_frame = ttkb.Frame(config_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        self.ignore_case = ttkb.BooleanVar(value=True)
        ttkb.Checkbutton(options_frame, text="忽略大小写", 
                        variable=self.ignore_case,
                        command=self._on_filter_change).grid(row=0, column=0, padx=5)
        
        self.live_preview = ttkb.BooleanVar(value=False)
        ttkb.Checkbutton(options_frame, text="实时预览", 
                        variable=self.live_preview,
                        command=self.app.toggle_live_preview).grid(row=0, column=1, padx=5)
        
        self.hide_fields = ttkb.BooleanVar(value=True)
        ttkb.Checkbutton(options_frame, text="启用字段过滤", 
                        variable=self.hide_fields,
                        command=self._on_filter_change).grid(row=0, column=2, padx=5)
        
        # 编码选择
        ttkb.Label(config_frame, text="输入编码:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.enc_in = ttkb.Combobox(config_frame, values=['ANSI','utf-8', 'gbk', 'gb2312', 'latin1'])
        self.enc_in.set('ANSI')
        self.enc_in.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.enc_in.bind('<<ComboboxSelected>>', lambda e: self._on_filter_change())
        
        ttkb.Label(config_frame, text="输出编码:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.enc_out = ttkb.Combobox(config_frame, values=['ANSI','utf-8', 'gbk', 'gb2312', 'latin1'])
        self.enc_out.set('ANSI')
        self.enc_out.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        
        # 按钮区域
        button_frame = ttkb.Frame(config_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        ttkb.Button(button_frame, text="开始过滤", 
                   command=self.app.start_filter, 
                   bootstyle="primary").pack(side="left", padx=5)
        ttkb.Button(button_frame, text="导出结果", 
                   command=self.app.export_filtered,
                   bootstyle="secondary").pack(side="right", padx=5)
        
        config_frame.columnconfigure(1, weight=1)
        config_frame.pack(fill="x", padx=5, pady=5)

    def _on_filter_change(self, *args):
        """过滤条件变化时的处理"""
        if hasattr(self.app, 'current_file') and self.live_preview.get():
            self.app.preview_filtered()

    def get_config(self):
        """获取当前配置"""
        return {
            'keywords': self.keyword.get(),
            'filter_fields': self.filter_fields.get(),
            'ignore_case': self.ignore_case.get(),
            'enable_field_filter': self.hide_fields.get(),
            'read_enc': self.enc_in.get(),
            'write_enc': self.enc_out.get()
        }