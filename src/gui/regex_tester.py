import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import re
from pathlib import Path
import json

class RegexTester:
    """正则表达式测试工具"""
    
    def __init__(self, parent):
        self.window = ttkb.Toplevel(parent)
        self.window.title("正则表达式测试工具")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # 加载历史记录
        self.history_file = Path.home() / '.logwatch' / 'regex_history.json'
        self.history_file.parent.mkdir(exist_ok=True)
        self.load_history()
        
        self._create_widgets()
        self._center_window()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 主分割面板
        main_pane = ttkb.PanedWindow(self.window, orient=HORIZONTAL)
        main_pane.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 左侧面板（历史记录）
        left_frame = ttkb.Labelframe(main_pane, text="历史记录")
        main_pane.add(left_frame, weight=1)
        
        # 历史记录列表
        self.history_list = ttkb.Treeview(
            left_frame,
            columns=("pattern",),
            show="headings",
            selectmode="browse"
        )
        self.history_list.heading("pattern", text="正则表达式")
        self.history_list.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 绑定双击事件
        self.history_list.bind("<Double-1>", self._on_history_select)
        
        # 右侧面板（测试区域）
        right_frame = ttkb.Frame(main_pane)
        main_pane.add(right_frame, weight=3)
        
        # 输入区域
        input_frame = ttkb.Labelframe(right_frame, text="正则表达式", padding=5)
        input_frame.pack(fill=X, padx=5, pady=5)
        
        # 正则表达式输入框和选项
        regex_frame = ttkb.Frame(input_frame)
        regex_frame.pack(fill=X)
        
        self.regex_var = tk.StringVar()
        self.regex_entry = ttkb.Entry(regex_frame, textvariable=self.regex_var)
        self.regex_entry.pack(side=LEFT, fill=X, expand=True)
        
        # 选项区域
        option_frame = ttkb.Frame(input_frame)
        option_frame.pack(fill=X, pady=5)
        
        self.ignore_case = ttkb.BooleanVar()
        ttkb.Checkbutton(option_frame, text="忽略大小写",
                       variable=self.ignore_case,
                       command=self._update_matches).pack(side=LEFT)
                       
        self.multiline = ttkb.BooleanVar()
        ttkb.Checkbutton(option_frame, text="多行模式",
                       variable=self.multiline,
                       command=self._update_matches).pack(side=LEFT)
                       
        self.dot_all = ttkb.BooleanVar()
        ttkb.Checkbutton(option_frame, text="点号匹配换行",
                       variable=self.dot_all,
                       command=self._update_matches).pack(side=LEFT)
        
        # 测试文本区域
        test_frame = ttkb.Labelframe(right_frame, text="测试文本", padding=5)
        test_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.test_text = ttkb.Text(test_frame, wrap=WORD, height=10)
        self.test_text.pack(fill=BOTH, expand=True)
        
        # 匹配结果区域
        result_frame = ttkb.Labelframe(right_frame, text="匹配结果", padding=5)
        result_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.result_text = ttkb.Text(result_frame, wrap=WORD, height=8)
        self.result_text.pack(fill=BOTH, expand=True)
        
        # 按钮区域
        button_frame = ttkb.Frame(right_frame)
        button_frame.pack(fill=X, padx=5, pady=5)
        
        ttkb.Button(button_frame, text="测试",
                   command=self._update_matches,
                   bootstyle="primary").pack(side=LEFT, padx=5)
                   
        ttkb.Button(button_frame, text="清空",
                   command=self._clear_all,
                   bootstyle="secondary").pack(side=LEFT, padx=5)
                   
        ttkb.Button(button_frame, text="添加到历史",
                   command=self._add_to_history,
                   bootstyle="info").pack(side=LEFT, padx=5)
        
        # 绑定事件
        self.regex_var.trace_add("write", lambda *args: self._update_matches())
        self.test_text.bind("<KeyRelease>", lambda e: self._update_matches())
        
    def _center_window(self):
        """使窗口居中显示"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() - width) // 2
        y = (self.window.winfo_screenheight() - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
    def _update_matches(self, *args):
        """更新匹配结果"""
        pattern = self.regex_var.get()
        if not pattern:
            self.result_text.delete("1.0", END)
            return
            
        try:
            # 构建正则表达式标志
            flags = 0
            if self.ignore_case.get():
                flags |= re.IGNORECASE
            if self.multiline.get():
                flags |= re.MULTILINE
            if self.dot_all.get():
                flags |= re.DOTALL
                
            regex = re.compile(pattern, flags)
            text = self.test_text.get("1.0", "end-1c")
            
            # 清除现有的标签
            for tag in self.test_text.tag_names():
                if tag.startswith("match"):
                    self.test_text.tag_remove(tag, "1.0", END)
            
            # 查找所有匹配
            matches = list(regex.finditer(text))
            
            # 更新结果文本
            self.result_text.delete("1.0", END)
            if matches:
                self.result_text.insert(END, f"找到 {len(matches)} 个匹配：\n\n")
                for i, match in enumerate(matches, 1):
                    # 添加匹配标记
                    start_idx = f"1.0+{match.start()}c"
                    end_idx = f"1.0+{match.end()}c"
                    self.test_text.tag_add(f"match_{i}", start_idx, end_idx)
                    self.test_text.tag_configure(f"match_{i}", background="yellow")
                    
                    # 显示匹配信息
                    self.result_text.insert(END, f"匹配 {i}:\n")
                    self.result_text.insert(END, f"位置: {match.start()}-{match.end()}\n")
                    self.result_text.insert(END, f"内容: {match.group()}\n")
                    
                    # 显示分组信息
                    if match.groups():
                        self.result_text.insert(END, "分组:\n")
                        for j, group in enumerate(match.groups(), 1):
                            self.result_text.insert(END, f"  {j}: {group}\n")
                    self.result_text.insert(END, "\n")
            else:
                self.result_text.insert(END, "没有找到匹配")
                
        except re.error as e:
            self.result_text.delete("1.0", END)
            self.result_text.insert(END, f"正则表达式错误: {str(e)}")
            
    def _clear_all(self):
        """清空所有输入"""
        self.regex_var.set("")
        self.test_text.delete("1.0", END)
        self.result_text.delete("1.0", END)
        self.ignore_case.set(False)
        self.multiline.set(False)
        self.dot_all.set(False)
        
    def _add_to_history(self):
        """添加当前正则表达式到历史记录"""
        pattern = self.regex_var.get()
        if pattern and pattern not in self.history:
            self.history.insert(0, pattern)
            if len(self.history) > 20:  # 限制历史记录数量
                self.history.pop()
            self._update_history_list()
            self.save_history()
            
    def _on_history_select(self, event):
        """从历史记录中选择正则表达式"""
        selection = self.history_list.selection()
        if selection:
            item = self.history_list.item(selection[0])
            self.regex_var.set(item['values'][0])
            
    def _update_history_list(self):
        """更新历史记录列表"""
        for item in self.history_list.get_children():
            self.history_list.delete(item)
        for pattern in self.history:
            self.history_list.insert("", END, values=(pattern,))
            
    def load_history(self):
        """加载历史记录"""
        try:
            if self.history_file.exists():
                with self.history_file.open('r', encoding='utf-8') as f:
                    self.history = json.load(f)
            else:
                self.history = []
        except Exception:
            self.history = []
            
    def save_history(self):
        """保存历史记录"""
        try:
            with self.history_file.open('w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存历史记录失败: {e}")
            
    @classmethod
    def show_dialog(cls, parent):
        """显示正则表达式测试对话框"""
        dialog = cls(parent)
        return dialog