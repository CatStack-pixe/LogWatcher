import os
import sys
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import re
from datetime import datetime
from typing import List
import multiprocessing

# 导入其他模块
from src.gui.file_panel import FilePanel
from src.gui.config_panel import ConfigPanel
from src.core.log_processor import LogProcessor
from src.core.log_monitor import LogMonitor
from src.utils.tooltip import ToolTip
from src.utils.config_manager import ConfigManager
from src.utils.exporter import LogExporter
from src.utils.recent_files import RecentFiles
from src.gui.search_dialog import SearchDialog
from src.utils.thread_pool import ThreadPoolManager
from src.gui.regex_tester import RegexTester
from src.core.log_analyzer import LogAnalyzer

class LogFilterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 加载配置
        self.config_manager = ConfigManager()
        self.recent_files = RecentFiles(self.config_manager.config_dir)
        config = self.config_manager.load_config()
        
        # 设置主题
        self.style = ttkb.Style(theme=config.get('theme', 'litera'))
        
        self.title("日志过滤工具")
        self.geometry(config.get('window_size', "1500x750"))
        
        # 初始化处理器和队列
        self.log_processor = LogProcessor(self)
        self.log_monitor = LogMonitor(self.on_log_update)
        self.processing_queue = queue.Queue()
        
        # 初始化线程池
        self.thread_pool = ThreadPoolManager(max_workers=multiprocessing.cpu_count())
        
        # 初始化颜色方案
        self.custom_colors = {
            'bg': '#ffffff',
            'fg': '#333333',
            'accent': '#0d6efd',
            'selection': '#e9ecef',
            'border': '#dee2e6'
        }
        
        # 设置程序图标
        self._set_icon()
        
        self.configure(bg=self.custom_colors['bg'])
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 创建主界面
        self._create_widgets()
        self._setup_bindings()
        self.after(100, self.process_queue)
        
        # 窗口居中显示
        self.center_window()

    def toggle_live_preview(self):
        """处理实时预览切换"""
        if hasattr(self, 'current_file'):
            if self.config_panel.live_preview.get():
                self.preview_filtered()
                self._update_system_info("已开启实时预览")
            else:
                self.dst_preview.config(state="normal")
                self.dst_preview.delete("1.0", "end")
                self.dst_preview.config(state="disabled")
                self._update_system_info("已关闭实时预览")

    def _set_icon(self):
        """设置程序图标"""
        try:
            icon_path = Path(__file__).parent.parent.parent / "resources/icon.ico"
            if icon_path.exists():
                self.iconbitmap(icon_path)
        except Exception as e:
            self.log_error(f"加载图标失败: {e}")

    def start_filter(self):
        """开始过滤操作"""
        if not hasattr(self, 'current_file'):
            self.log_error("请先选择要过滤的文件")
            return

        output_path = self.current_file.parent / f"{self.current_file.stem}_filtered{self.current_file.suffix}"
        self.show_progress()

        def do_filter():
            try:
                config = self.config_panel.get_config()
                count_in, count_out = self.log_processor.filter_log(
                    self.current_file,
                    output_path,
                    preview_mode=False,
                    **config
                )
                self.log_info(f"✅ 过滤完成")
                self.log_info(f"   - 读取：{count_in} 行")
                self.log_info(f"   - 匹配：{count_out} 行")
                self.log_info(f"   - 输出文件：{output_path}")

            except Exception as e:
                self.log_error(f"过滤过程出错：{e}")
            finally:
                self.processing_queue.put(('progress_done', None))

        # 在新线程中执行过滤
        threading.Thread(target=do_filter, daemon=True).start()

    def _create_widgets(self):
        """创建主界面部件"""
        # 创建主容器
        main_container = ttkb.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # 创建水平分割的主面板
        self.main_pane = ttkb.PanedWindow(main_container, orient=HORIZONTAL)
        self.main_pane.pack(fill=BOTH, expand=True)

        # 创建左侧工具栏容器
        self.toolbar_container = ttkb.Frame(self.main_pane, width=50)
        self._build_toolbar(self.toolbar_container)
        self.main_pane.add(self.toolbar_container, weight=0)

        # 左侧面板
        self.left_frame = ttkb.Frame(self.main_pane)
        self.file_panel = FilePanel(self.left_frame, self)
        self.config_panel = ConfigPanel(self.left_frame, self)
        self.main_pane.add(self.left_frame, weight=1)

        # 右侧面板
        self.right_pane = ttkb.PanedWindow(self.main_pane, orient=VERTICAL)
        self._build_preview_panel(self.right_pane)
        self.main_pane.add(self.right_pane, weight=3)

        # 底部状态栏
        self._build_status_bar()
        
        # 加载上次使用的过滤器配置
        self._load_filter_config()

    def _build_toolbar(self, parent):
        """创建左侧工具栏"""
        toolbar_frame = ttkb.Frame(parent)
        toolbar_frame.pack(fill=Y, expand=True)
        parent.configure(width=50)
        
        tools = [
            ("🔍", "搜索模式", self.switch_to_search),
            ("📈", "统计分析", self.show_analysis),
            ("📡", "实时监控", self.switch_to_monitor),
            ("🧪", "正则测试", self.show_regex_tester),
            ("⚙️", "设置", self.switch_to_settings),
            ("❓", "帮助", self.show_help),
            ("📤", "导出", self.export_filtered),
            ("📋", "最近文件", self.show_recent_files)
        ]
        
        self.toolbar_buttons = []
        for icon, tooltip, command in tools:
            btn = ttkb.Button(
                toolbar_frame,
                text=icon,
                bootstyle="link",
                width=2,
                command=command
            )
            self.toolbar_buttons.append(btn)
            ToolTip(btn, text=tooltip)
            btn.pack(pady=5)

    def show_analysis(self):
        """显示统计分析对话框"""
        if not hasattr(self, 'current_file'):
            self.log_error("请先选择要分析的文件")
            return
            
        # 创建分析对话框
        analysis_window = ttkb.Toplevel(self)
        analysis_window.title("日志分析")
        analysis_window.geometry("800x600")
        
        # 创建选项卡
        notebook = ttkb.Notebook(analysis_window)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # 配置选项卡
        config_frame = ttkb.Frame(notebook)
        notebook.add(config_frame, text="分析配置")
        
        # 选项设置
        ttkb.Label(config_frame, text="文件编码:").pack(anchor=W, padx=10, pady=5)
        encoding = ttkb.Combobox(config_frame, values=['auto', 'utf-8', 'gbk', 'gb2312', 'latin1'])
        encoding.set('auto')
        encoding.pack(fill=X, padx=10, pady=5)
        
        options_frame = ttkb.Labelframe(config_frame, text="分析项目", padding=10)
        options_frame.pack(fill=X, padx=10, pady=5)
        
        analyze_time = ttkb.BooleanVar(value=True)
        analyze_level = ttkb.BooleanVar(value=True)
        analyze_words = ttkb.BooleanVar(value=True)
        analyze_basic = ttkb.BooleanVar(value=True)
        
        ttkb.Checkbutton(options_frame, text="时间分布分析", 
                       variable=analyze_time).pack(anchor=W)
        ttkb.Checkbutton(options_frame, text="日志级别分析", 
                       variable=analyze_level).pack(anchor=W)
        ttkb.Checkbutton(options_frame, text="关键词频率分析", 
                       variable=analyze_words).pack(anchor=W)
        ttkb.Checkbutton(options_frame, text="基本统计信息", 
                       variable=analyze_basic).pack(anchor=W)
        
        output_frame = ttkb.Labelframe(config_frame, text="输出选项", padding=10)
        output_frame.pack(fill=X, padx=10, pady=5)
        
        export_txt = ttkb.BooleanVar(value=True)
        export_excel = ttkb.BooleanVar(value=True)
        export_charts = ttkb.BooleanVar(value=True)
        
        ttkb.Checkbutton(output_frame, text="导出文本报告", 
                       variable=export_txt).pack(anchor=W)
        ttkb.Checkbutton(output_frame, text="导出Excel统计表", 
                       variable=export_excel).pack(anchor=W)
        ttkb.Checkbutton(output_frame, text="生成统计图表", 
                       variable=export_charts).pack(anchor=W)
        
        # 开始分析按钮
        def start_analysis():
            try:
                analyzer = LogAnalyzer()
                
                # 创建输出目录
                output_dir = self.current_file.parent / "analysis_results"
                output_dir.mkdir(exist_ok=True)
                
                # 显示进度窗口
                self.show_progress()
                
                def do_analysis():
                    try:
                        # 获取分析结果
                        stats = analyzer.analyze_log(
                            self.current_file,
                            encoding=None if encoding.get() == 'auto' else encoding.get()
                        )
                        
                        # 根据选项导出结果
                        if export_txt.get():
                            report_path = output_dir / f"{self.current_file.stem}_analysis.txt"
                            analyzer.export_analysis_report(stats, report_path)
                            self.log_info(f"✅ 已导出分析报告: {report_path}")
                            
                        if export_excel.get():
                            excel_path = output_dir / f"{self.current_file.stem}_stats.xlsx"
                            analyzer.export_to_excel(stats, excel_path)
                            self.log_info(f"✅ 已导出Excel报表: {excel_path}")
                            
                        if export_charts.get():
                            if analyze_time.get():
                                time_chart_path = output_dir / f"{self.current_file.stem}_time_dist.png"
                                analyzer.generate_time_distribution_chart(stats, time_chart_path)
                                self.log_info(f"✅ 已生成时间分布图: {time_chart_path}")
                                
                            if analyze_level.get() and stats['level_distribution']:
                                level_chart_path = output_dir / f"{self.current_file.stem}_level_dist.png"
                                analyzer.generate_level_distribution_chart(stats, level_chart_path)
                                self.log_info(f"✅ 已生成级别分布图: {level_chart_path}")
                                
                        # 显示基本统计信息
                        if analyze_basic.get():
                            basic_stats = f"""
基本统计信息:
总行数: {stats['total_lines']}
空行数: {stats['empty_lines']}
平均行长度: {stats['line_length_avg']:.2f} 字符
检测到的时间格式: {stats['timestamp_pattern']}
"""
                            self.update_system_info(basic_stats)
                            
                    except Exception as e:
                        self.log_error(f"分析过程出错: {e}")
                    finally:
                        self.processing_queue.put(('progress_done', None))
                        
                # 在新线程中执行分析
                threading.Thread(target=do_analysis, daemon=True).start()
                
                # 关闭分析窗口
                analysis_window.destroy()
                
            except Exception as e:
                self.log_error(f"启动分析失败: {e}")
                
        button_frame = ttkb.Frame(config_frame)
        button_frame.pack(fill=X, padx=10, pady=10)
        
        ttkb.Button(button_frame,
                   text="开始分析",
                   command=start_analysis,
                   bootstyle="primary").pack(side=LEFT, padx=5)
                   
        ttkb.Button(button_frame,
                   text="取消",
                   command=analysis_window.destroy,
                   bootstyle="secondary").pack(side=LEFT, padx=5)
        
        # 窗口居中
        analysis_window.transient(self)
        analysis_window.grab_set()
        analysis_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - analysis_window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - analysis_window.winfo_height()) // 2
        analysis_window.geometry(f"+{x}+{y}")

    def show_regex_tester(self):
        """显示正则表达式测试工具"""
        RegexTester.show_dialog(self)

    def _build_preview_panel(self, parent):
        """创建预览面板"""
        # 创建上方的系统信息面板
        self.info_frame = ttkb.Labelframe(parent, text="系统信息", bootstyle="info")
        
        # 添加系统信息文本框
        self.system_info = scrolledtext.ScrolledText(
            self.info_frame, 
            height=8,
            wrap=WORD,
            bg='white',
            fg='#333333',
            insertbackground='#333333',
            relief="solid",
            font=("Segoe UI", 10)
        )
        self.system_info.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        parent.add(self.info_frame)

        # 创建预览容器
        preview_frame = ttkb.Frame(parent)
        parent.add(preview_frame)

        # 创建行号文本框和预览文本框的容器
        content_frame = ttkb.Frame(preview_frame)
        content_frame.pack(fill=BOTH, expand=True)

        # 创建行号文本框
        self.line_numbers = tk.Text(
            content_frame,
            width=6,
            padx=3,
            takefocus=0,
            border=0,
            background='#f0f0f0',
            foreground='#606060',
            wrap=NONE,
            font=("Cascadia Code", 10)
        )
        self.line_numbers.pack(side=LEFT, fill=Y)

        # 创建预览文本框
        preview_container = ttkb.Frame(content_frame)
        preview_container.pack(side=LEFT, fill=BOTH, expand=True)

        # 使用Text组件替换ScrolledText，手动添加滚动条
        self.dst_preview = tk.Text(
            preview_container,
            wrap=WORD,
            bg='white',
            fg='#333333',
            insertbackground='#333333',
            relief="solid",
            font=("Cascadia Code", 10),
            undo=True,
            maxundo=0
        )
        scrollbar = ttkb.Scrollbar(preview_container, command=self._on_preview_scroll)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.dst_preview.pack(side=LEFT, fill=BOTH, expand=True)
        self.dst_preview.configure(yscrollcommand=scrollbar.set)

        # 禁用行号编辑
        self.line_numbers.config(state='disabled')

        # 绑定文本变化事件
        self.dst_preview.bind('<<Modified>>', self._on_text_modified)
        self.dst_preview.edit_modified(False)  # 重置修改标志

    def _on_text_modified(self, event=None):
        """处理文本变化事件"""
        if self.dst_preview.edit_modified():
            self._update_line_numbers()
            self.dst_preview.edit_modified(False)  # 重置修改标志

    def _on_preview_scroll(self, *args):
        """同步滚动预览区域和行号"""
        if len(args) > 0:
            self.dst_preview.yview(*args)
            self.line_numbers.yview(*args)

    def _update_line_numbers(self, event=None):
        """更新行号显示"""
        if not hasattr(self, 'line_numbers'):
            return
            
        # 获取总行数
        text = self.dst_preview.get('1.0', 'end-1c')
        line_count = text.count('\n') + 1
        
        # 更新行号文本
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', 'end')
        lines = '\n'.join(str(i).rjust(4) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', lines)
        self.line_numbers.config(state='disabled')
        
        # 同步滚动位置
        self.line_numbers.yview_moveto(self.dst_preview.yview()[0])

    def _highlight_keywords(self, keywords, ignore_case=True):
        """高亮关键字"""
        if not keywords:
            return
            
        # 移除现有的高亮标签
        for tag in self.dst_preview.tag_names():
            if tag.startswith("keyword_"):
                self.dst_preview.tag_delete(tag)
                
        content = self.dst_preview.get("1.0", "end-1c")
        
        # 为每个关键字创建不同的高亮颜色
        colors = ['#ffeb3b', '#ffa726', '#4caf50', '#03a9f4', '#e91e63']
        
        for i, keyword in enumerate(keywords):
            color = colors[i % len(colors)]
            tag_name = f"keyword_{i}"
            self.dst_preview.tag_configure(tag_name, background=color)
            
            start = "1.0"
            while True:
                if ignore_case:
                    pos = self.dst_preview.search(keyword, start, "end", nocase=True)
                else:
                    pos = self.dst_preview.search(keyword, start, "end")
                    
                if not pos:
                    break
                    
                end = f"{pos}+{len(keyword)}c"
                self.dst_preview.tag_add(tag_name, pos, end)
                start = end

    def _build_status_bar(self):
        """创建状态栏"""
        status_frame = ttkb.Frame(self)
        status_frame.pack(fill="x", side="bottom", pady=2)
        
        # 添加进度条（默认隐藏）
        self.progress_bar = ttkb.Progressbar(
            status_frame, 
            mode='indeterminate',
            bootstyle="primary"
        )
        self.progress_bar.pack(fill="x", padx=5, pady=2)
        self.progress_bar.pack_forget()
        
        # 添加控制台输出区域
        self.console = scrolledtext.ScrolledText(
            status_frame,
            height=5,
            wrap=WORD,
            bg='white',
            fg='#333333',
            insertbackground='#333333',
            relief="solid",
            font=("Segoe UI", 9)
        )
        self.console.pack(fill="x", padx=5, pady=(0, 2))
        self.console.insert("1.0", "准备就绪...\n")
        self.console.config(state="disabled")

    def _setup_bindings(self):
        """设置快捷键绑定"""
        self.bind("<Control-o>", lambda e: self.file_panel.load_directory())
        self.bind("<Control-r>", lambda e: self.file_panel.refresh_files())
        self.bind("<Control-p>", lambda e: self.batch_process())
        self.bind("<F5>", lambda e: self.file_panel.refresh_files())

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_file_select(self, event):
        """文件选择事件处理"""
        selected = self.file_panel.get_selected_files()
        if selected:
            self.current_file = selected[0]
            # 添加到最近文件列表
            self.recent_files.add_file(self.current_file)
            self._update_system_info()
            if self.config_panel.live_preview.get():
                self._apply_theme_colors()
                self.preview_filtered()

    def _update_system_info(self, additional_info=None):
        """更新系统信息显示"""
        try:
            self.system_info.config(state="normal")
            self.system_info.delete("1.0", "end")
            
            info = []
            info.append(f"程序版本: v1.3")
            info.append(f"操作系统: {os.name.upper()}")
            info.append(f"Python版本: {sys.version.split()[0]}")
            
            if hasattr(self, 'current_file'):
                info.append(f"\n当前文件: {self.current_file.name}")
                size = self.current_file.stat().st_size // 1024
                info.append(f"文件大小: {size} KB")
            
            if additional_info:
                info.append(f"\n{additional_info}")
            
            self.system_info.insert("1.0", "\n".join(info))
            self.system_info.config(state="disabled")
            
        except Exception as e:
            self.log_error(f"更新系统信息失败: {e}")

    def update_system_info(self, additional_info: str):
        """更新系统信息显示区域内容"""
        if hasattr(self, 'system_info'):
            self.system_info.config(state="normal")
            self.system_info.delete("1.0", "end")
            self.system_info.insert("1.0", additional_info)
            self.system_info.config(state="disabled")

    def _apply_theme_colors(self):
        """应用当前主题的颜色"""
        theme_name = self.style.theme_use()
        if theme_name in ['darkly', 'superhero', 'solar', 'cyborg']:
            bg_color = self.style.colors.dark
            fg_color = self.style.colors.light
        else:
            bg_color = self.style.colors.light
            fg_color = self.style.colors.dark
            
        for widget in [self.dst_preview, self.system_info, self.console]:
            widget.configure(
                bg=bg_color,
                fg=fg_color,
                insertbackground=fg_color
            )

    def preview_filtered(self):
        """预览过滤结果"""
        if not hasattr(self, 'current_file'):
            return
            
        config = self.config_panel.get_config()
        # 直接使用从 config_panel 获取的配置，不需要重新映射参数名
        self.log_processor.filter_log(
            self.current_file,
            None,  # 预览模式不需要输出文件
            preview_mode=True,
            **config
        )

    def batch_process(self):
        """批量处理文件"""
        files = self.file_panel.get_selected_files()
        if not files:
            self.log_error("请先选择要处理的文件")
            return
            
        # 创建输出目录
        output_dir = self.file_panel.current_dir / "filtered"
        output_dir.mkdir(exist_ok=True)
        
        # 获取过滤配置
        config = self.config_panel.get_config()
        
        # 显示进度窗口
        self.show_progress()
        
        def process_file(file_path):
            """处理单个文件"""
            try:
                output_path = output_dir / f"{file_path.stem}_filtered{file_path.suffix}"
                return self.log_processor.filter_log(
                    file_path,
                    output_path,
                    preview_mode=False,
                    **config
                )
            except Exception as e:
                self.log_error(f"处理文件 {file_path.name} 时出错: {e}")
                return (0, 0)
                
        def on_file_complete(file_path, result):
            """文件处理完成回调"""
            count_in, count_out = result
            if count_in > 0:
                self.log_info(f"✅ 完成：{file_path.name}")
                self.log_info(f"   - 读取: {count_in} 行")
                self.log_info(f"   - 匹配: {count_out} 行")
                
        # 重置处理器统计信息
        self.log_processor.processing_stats = {"total": 0, "matched": 0}
        
        # 提交任务到线程池
        self.thread_pool.map(process_file, files, callback=on_file_complete)
        
        # 开始监控任务进度
        def check_progress():
            if not self.thread_pool.is_running:
                # 获取总体统计信息
                stats = self.log_processor.processing_stats
                total_in = stats["total"]
                total_out = stats["matched"]
                
                # 显示总结信息
                self.log_info(f"\n✅ 批量处理完成")
                self.log_info(f"   - 总行数: {total_in}")
                self.log_info(f"   - 匹配行数: {total_out}")
                percent = (total_out / total_in * 100) if total_in > 0 else 0
                self.log_info(f"   - 匹配率: {percent:.2f}%")
                self.log_info(f"   - 输出目录: {output_dir}")
                
                # 关闭进度窗口
                self.stop_progress()
                return
                
            # 更新进度信息
            completed = len(self.thread_pool.get_results())
            total = len(files)
            percent = (completed / total) * 100
            self.update_progress(f"处理进度: {completed}/{total} 文件 ({percent:.1f}%)")
            
            # 继续检查进度
            self.after(100, check_progress)
            
        # 启动进度检查
        check_progress()

    def log_error(self, msg):
        """记录错误信息"""
        self.processing_queue.put(('error', f"❌ {msg}"))

    def log_info(self, msg):
        """记录信息"""
        self.processing_queue.put(('info', f"ℹ️ {msg}"))

    def process_queue(self):
        """处理消息队列"""
        while not self.processing_queue.empty():
            msg_type, msg = self.processing_queue.get()
            if msg_type == 'progress_done':
                self.stop_progress()
            else:
                self.console.config(state="normal")
                self.console.insert("end", msg + "\n")
                self.console.see("end")
                self.console.config(state="disabled")
        self.after(100, self.process_queue)

    def show_progress(self):
        """显示进度条"""
        self.progress_bar.pack(fill="x", padx=5, pady=2)
        self.progress_bar.start(10)

    def stop_progress(self):
        """停止进度条"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

    def update_progress(self, message):
        """更新进度信息"""
        self.console.config(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.config(state="disabled")

    def on_close(self):
        """窗口关闭处理"""
        if self.thread_pool.is_running:
            if not messagebox.askyesno("确认", "有正在进行的处理任务，确定要退出吗？"):
                return
            self.thread_pool.shutdown(wait=False)
        self._save_current_config()  # 保存配置
        if self.log_monitor.is_monitoring:
            self.log_monitor.stop_monitoring()
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
        self.quit()

    def _load_filter_config(self):
        """加载过滤器配置"""
        filters = self.config_manager.get_value('filters', {})
        if filters:
            self.config_panel.keyword.delete(0, tk.END)
            self.config_panel.keyword.insert(0, filters.get('keyword', '[CHAT]'))
            
            self.config_panel.filter_fields.delete(0, tk.END)
            self.config_panel.filter_fields.insert(0, filters.get('filter_fields', ''))
            
            self.config_panel.ignore_case.set(filters.get('ignore_case', True))
            self.config_panel.hide_fields.set(filters.get('hide_fields', True))
            
            self.config_panel.enc_in.set(filters.get('enc_in', 'ANSI'))
            self.config_panel.enc_out.set(filters.get('enc_out', 'ANSI'))
            
    def _save_current_config(self):
        """保存当前配置"""
        # 保存窗口大小
        self.config_manager.update_config('window_size', self.geometry())
        
        # 保存主题
        self.config_manager.update_config('theme', self.style.theme_use())
        
        # 保存过滤器配置
        filters = self.config_panel.get_config()
        self.config_manager.update_config('filters', filters)

    # 工具栏功能函数
    def switch_to_search(self):
        """切换到搜索模式"""
        search_config = SearchDialog.show_dialog(self)
        if not search_config:
            return
            
        # 清空预览区域
        self.dst_preview.config(state="normal")
        self.dst_preview.delete("1.0", "end")
        
        # 根据搜索范围获取文件列表
        files_to_search = []
        if search_config['range'] == 'current' and hasattr(self, 'current_file'):
            files_to_search = [self.current_file]
        elif search_config['range'] == 'selected':
            files_to_search = self.file_panel.get_selected_files()
        elif search_config['range'] == 'all' and self.file_panel.current_dir:
            files_to_search = list(self.file_panel.current_dir.glob('*.log')) + \
                            list(self.file_panel.current_dir.glob('*.txt'))
                            
        if not files_to_search:
            self.log_error("没有找到要搜索的文件")
            return
            
        # 开始搜索
        self.show_progress()
        threading.Thread(target=self._do_search, 
                       args=(files_to_search, search_config),
                       daemon=True).start()
    
    def _do_search(self, files: List[Path], config: dict):
        """执行搜索"""
        try:
            total_matches = 0
            pattern = config['text']
            if not config['use_regex']:
                pattern = re.escape(pattern)
            
            flags = 0 if config['case_sensitive'] else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            for file in files:
                try:
                    with file.open('r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                self.processing_queue.put(('info', 
                                    f"[{file.name}:{i}] {line.strip()}"))
                                total_matches += 1
                                
                except Exception as e:
                    self.log_error(f"处理文件 {file.name} 时出错: {e}")
                    
            self.processing_queue.put(('info', f"\n共找到 {total_matches} 个匹配"))
            
        except re.error as e:
            self.log_error(f"正则表达式错误: {e}")
        except Exception as e:
            self.log_error(f"搜索过程出错: {e}")
        finally:
            self.processing_queue.put(('progress_done', None))
            
    def switch_to_monitor(self):
        """切换到实时监控模式"""
        if not hasattr(self, 'current_file'):
            self.log_error("请先选择要监控的文件")
            return
            
        if self.log_monitor.is_monitoring:
            self.log_monitor.stop_monitoring()
            self.log_info("停止监控")
            # 更新工具栏按钮状态
            self.toolbar_buttons[1].configure(text="📡")
        else:
            self.log_monitor.start_monitoring(self.current_file)
            self.log_info(f"开始监控: {self.current_file.name}")
            # 更新工具栏按钮状态
            self.toolbar_buttons[1].configure(text="⏹️")
            
    def switch_to_settings(self):
        """切换到设置界面"""
        settings_window = ttkb.Toplevel(self)
        settings_window.title("设置")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        
        # 主题设置
        theme_frame = ttkb.Labelframe(settings_window, text="主题设置", padding=10)
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        themes = ['litera', 'darkly', 'superhero', 'solar', 'cyborg']
        current_theme = self.style.theme_use()
        
        theme_var = ttkb.StringVar(value=current_theme)
        
        def on_theme_change():
            selected_theme = theme_var.get()
            self.style.theme_use(selected_theme)
            self._apply_theme_colors()
            self.config_manager.update_config('theme', selected_theme)
            self.log_info(f"已切换主题: {selected_theme}")
        
        for theme in themes:
            ttkb.Radiobutton(
                theme_frame, 
                text=theme.capitalize(),
                variable=theme_var,
                value=theme,
                command=on_theme_change
            ).pack(anchor="w", pady=2)
            
        # 保存按钮
        ttkb.Button(
            settings_window,
            text="确定",
            command=settings_window.destroy,
            bootstyle="primary"
        ).pack(side="bottom", pady=10)
        
        # 窗口居中
        settings_window.transient(self)
        settings_window.grab_set()
        settings_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - settings_window.winfo_width()) // 2
        y = (self.winfo_y() + (self.winfo_height() - settings_window.winfo_height()) // 2)
        settings_window.geometry(f"+{x}+{y}")
            
    def on_log_update(self, new_content: str):
        """处理新的日志内容"""
        config = self.config_panel.get_config()
        keywords = [k.strip() for k in config['keyword'].split('|') if k.strip()]
        
        # 应用过滤条件
        if keywords:
            lines = new_content.splitlines()
            filtered_lines = []
            for line in lines:
                if any(k.lower() in line.lower() if config['ignore_case'] else k in line 
                      for k in keywords):
                    if config['hide_fields'] and config['filter_fields']:
                        # 应用字段过滤
                        fields = [f.strip() for f in config['filter_fields'].split('|')]
                        for field in fields:
                            if config['ignore_case']:
                                field_pattern = field.lower()
                                line_lower = line.lower()
                                if field_pattern in line_lower:
                                    start_idx = line_lower.find(field_pattern)
                                    if start_idx >= 0:
                                        end_idx = start_idx + len(field)
                                        while end_idx < len(line) and line[end_idx] in ' :|\t':
                                            end_idx += 1
                                        line = line[:start_idx] + line[end_idx:]
                            else:
                                if field in line:
                                    start_idx = line.find(field)
                                    if start_idx >= 0:
                                        end_idx = start_idx + len(field)
                                        while end_idx < len(line) and line[end_idx] in ' :|\t':
                                            end_idx += 1
                                        line = line[:start_idx] + line[end_idx:]
                    filtered_lines.append(line)
            
            if filtered_lines:
                self.dst_preview.config(state="normal")
                for line in filtered_lines:
                    self.dst_preview.insert("end", line + "\n")
                self.dst_preview.see("end")
                self.dst_preview.config(state="disabled")
        else:
            # 没有关键字时显示所有新内容
            self.dst_preview.config(state="normal")
            self.dst_preview.insert("end", new_content)
            self.dst_preview.see("end")
            self.dst_preview.config(state="disabled")

    def show_help(self):
        """显示帮助文档"""
        help_window = ttkb.Toplevel(self)
        help_window.title("帮助文档")
        help_window.geometry("600x700")
        
        # 创建选项卡
        notebook = ttkb.Notebook(help_window)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # 基本使用选项卡
        basic_frame = ttkb.Frame(notebook)
        notebook.add(basic_frame, text="基本使用")
        
        basic_text = """
🔍 基本功能说明

1. 文件管理
   - 点击"打开目录"选择日志文件所在目录
   - 支持.log和.txt格式的文件
   - 可以选择多个文件进行批量处理

2. 过滤配置
   - 关键字：支持多个关键字，用"|"分隔
   - 删除字段：支持多个字段，用"|"分隔
   - 可以设置是否区分大小写
   - 支持不同的文件编码

3. 实时预览
   - 选中文件后自动显示过滤结果
   - 可以随时调整过滤条件
   
4. 批量处理
   - 选择多个文件后点击"批量处理"
   - 处理结果保存在"filtered"文件夹中

5. 实时监控
   - 点击工具栏的"📡"按钮开启监控
   - 自动显示新增的日志内容
   - 再次点击按钮停止监控
"""
        basic_help = scrolledtext.ScrolledText(basic_frame, wrap=WORD)
        basic_help.pack(fill=BOTH, expand=True, padx=5, pady=5)
        basic_help.insert("1.0", basic_text)
        basic_help.config(state="disabled")
        
        # 高级功能选项卡
        advanced_frame = ttkb.Frame(notebook)
        notebook.add(advanced_frame, text="高级功能")
        
        advanced_text = """
🔧 高级功能说明

1. 高级搜索
   - 支持正则表达式搜索
   - 可以在当前文件、选中文件或所有文件中搜索
   - 显示行号和文件名
   
2. 主题切换
   - 支持多种主题风格
   - 自动保存主题选择
   
3. 配置保存
   - 自动保存窗口大小和位置
   - 记住上次使用的过滤条件
   - 保存编码设置

4. 快捷键
   - Ctrl+O：打开目录
   - Ctrl+R：刷新文件列表
   - Ctrl+P：批量处理
   - F5：刷新
   - ESC：关闭对话框
"""
        advanced_help = scrolledtext.ScrolledText(advanced_frame, wrap=WORD)
        advanced_help.pack(fill=BOTH, expand=True, padx=5, pady=5)
        advanced_help.insert("1.0", advanced_text)
        advanced_help.config(state="disabled")
        
        # 关于选项卡
        about_frame = ttkb.Frame(notebook)
        notebook.add(about_frame, text="关于")
        
        about_text = """
ℹ️ 关于日志过滤工具

版本：v1.3
更新日期：2025-04-19

主要特性：
- 简单易用的图形界面
- 支持多文件批量处理
- 实时监控日志变化
- 高级搜索功能
- 主题切换
- 配置自动保存

使用中遇到问题？
请访问项目主页获取最新版本和帮助：
https://github.com/CatStack-pixe/LogWatcher

许可证：MIT
"""
        about_help = scrolledtext.ScrolledText(about_frame, wrap=WORD)
        about_help.pack(fill=BOTH, expand=True, padx=5, pady=5)
        about_help.insert("1.0", about_text)
        about_help.config(state="disabled")
        
        # 窗口居中
        help_window.transient(self)
        help_window.grab_set()
        help_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - help_window.winfo_width()) // 2
        y = (self.winfo_y() + (self.winfo_height() - help_window.winfo_height()) // 2)
        help_window.geometry(f"+{x}+{y}")

    def export_filtered(self):
        """导出过滤结果"""
        if not hasattr(self, 'current_file'):
            self.log_error("请先选择要导出的文件")
            return
            
        # 创建导出选项对话框
        export_window = ttkb.Toplevel(self)
        export_window.title("导出选项")
        export_window.geometry("400x300")
        export_window.resizable(False, False)
        
        # 导出格式选择
        format_frame = ttkb.Labelframe(export_window, text="导出格式", padding=10)
        format_frame.pack(fill="x", padx=10, pady=5)
        
        format_var = ttkb.StringVar(value="txt")
        formats = [
            ("纯文本 (*.txt)", "txt"),
            ("CSV文件 (*.csv)", "csv"),
            ("JSON文件 (*.json)", "json"),
            ("HTML文件 (*.html)", "html")
        ]
        
        for text, value in formats:
            ttkb.Radiobutton(format_frame, 
                           text=text,
                           variable=format_var,
                           value=value).pack(anchor="w", pady=2)
        
        # 选项框架
        options_frame = ttkb.Labelframe(export_window, text="导出选项", padding=10)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        include_line_numbers = ttkb.BooleanVar(value=True)
        ttkb.Checkbutton(options_frame, 
                       text="包含行号",
                       variable=include_line_numbers).pack(anchor="w")
                       
        # 按钮区域
        button_frame = ttkb.Frame(export_window)
        button_frame.pack(side="bottom", pady=10)
        
        def do_export():
            """执行导出操作"""
            try:
                # 获取文本内容
                content = self.dst_preview.get("1.0", "end-1c")
                lines = content.split('\n')
                
                # 根据选择的格式确定文件扩展名
                format_type = format_var.get()
                extensions = {
                    'txt': '.txt',
                    'csv': '.csv',
                    'json': '.json',
                    'html': '.html'
                }
                
                # 构造输出文件名
                base_name = self.current_file.stem
                output_path = self.current_file.parent / f"{base_name}_filtered{extensions[format_type]}"
                
                # 导出
                success = False
                if format_type == 'txt':
                    success = LogExporter.export_text(content, output_path)
                elif format_type == 'csv':
                    success = LogExporter.export_csv(lines, output_path)
                elif format_type == 'json':
                    success = LogExporter.export_json(lines, output_path)
                elif format_type == 'html':
                    success = LogExporter.export_html(lines, output_path)
                
                if success:
                    self.log_info(f"✅ 成功导出到: {output_path}")
                else:
                    self.log_error("❌ 导出失败")
                    
            except Exception as e:
                self.log_error(f"❌ 导出过程出错: {e}")
            finally:
                export_window.destroy()
        
        ttkb.Button(button_frame, 
                   text="导出",
                   command=do_export,
                   bootstyle="primary").pack(side="left", padx=5)
        ttkb.Button(button_frame,
                   text="取消",
                   command=export_window.destroy,
                   bootstyle="secondary").pack(side="left", padx=5)
        
        # 窗口居中
        export_window.transient(self)
        export_window.grab_set()
        export_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - export_window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - export_window.winfo_height()) // 2
        export_window.geometry(f"+{x}+{y}")

    def show_recent_files(self):
        """显示最近文件列表"""
        recent_window = ttkb.Toplevel(self)
        recent_window.title("最近文件")
        recent_window.geometry("500x400")
        
        # 创建文件列表
        list_frame = ttkb.Frame(recent_window)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # 创建列表视图
        columns = ("name", "path", "last_accessed", "size")
        tree = ttkb.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        
        # 设置列标题
        tree.heading("name", text="文件名")
        tree.heading("path", text="路径")
        tree.heading("last_accessed", text="最后访问时间")
        tree.heading("size", text="大小")
        
        # 设置列宽
        tree.column("name", width=150)
        tree.column("path", width=200)
        tree.column("last_accessed", width=150)
        tree.column("size", width=100)
        
        # 添加滚动条
        scrollbar = ttkb.Scrollbar(list_frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 加载最近文件列表
        recent_files = self.recent_files.get_valid_files()
        for file in recent_files:
            size_kb = int(file['size'] / 1024)
            last_accessed = datetime.fromisoformat(file['last_accessed']).strftime('%Y-%m-%d %H:%M')
            tree.insert("", "end", values=(
                file['name'],
                file['path'],
                last_accessed,
                f"{size_kb} KB"
            ))
            
        # 双击打开文件
        def on_double_click(event):
            item = tree.selection()[0]
            file_path = Path(tree.item(item)['values'][1])
            if file_path.exists():
                self.open_file(file_path)
                recent_window.destroy()
                
        tree.bind("<Double-1>", on_double_click)
        
        # 添加操作按钮
        button_frame = ttkb.Frame(recent_window)
        button_frame.pack(fill=X, padx=10, pady=5)
        
        def remove_selected():
            selected = tree.selection()
            if selected:
                item = selected[0]
                file_path = Path(tree.item(item)['values'][1])
                self.recent_files.remove_file(file_path)
                tree.delete(item)
                
        def clear_all():
            if messagebox.askyesno("确认", "确定要清空最近文件列表吗？"):
                self.recent_files.clear_files()
                tree.delete(*tree.get_children())
                
        ttkb.Button(button_frame,
                   text="打开所在目录",
                   command=lambda: os.startfile(Path(tree.item(tree.selection()[0])['values'][1]).parent) if tree.selection() else None,
                   bootstyle="primary").pack(side=LEFT, padx=5)
                   
        ttkb.Button(button_frame,
                   text="从列表移除",
                   command=remove_selected,
                   bootstyle="danger").pack(side=LEFT, padx=5)
                   
        ttkb.Button(button_frame,
                   text="清空列表",
                   command=clear_all,
                   bootstyle="warning").pack(side=LEFT, padx=5)
                   
        # 窗口居中
        recent_window.transient(self)
        recent_window.grab_set()
        recent_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - recent_window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - recent_window.winfo_height()) // 2
        recent_window.geometry(f"+{x}+{y}")
        
    def open_file(self, file_path: Path):
        """打开指定的文件"""
        if not file_path.exists():
            self.log_error(f"文件不存在: {file_path}")
            return
            
        # 设置当前目录
        self.file_panel.current_dir = file_path.parent
        self.file_panel.refresh_files()
        
        # 选中文件
        self.file_panel.file_list.selection_set(file_path.name)
        self.current_file = file_path
        
        # 添加到最近文件列表
        self.recent_files.add_file(file_path)
        
        # 更新预览
        if self.config_panel.live_preview.get():
            self.preview_filtered()

    def update_preview_content(self, content: str):
        """更新预览区域的内容"""
        if hasattr(self, 'dst_preview'):
            self.dst_preview.config(state="normal")
            self.dst_preview.delete("1.0", "end")
            self.dst_preview.insert("1.0", content)
            self.dst_preview.config(state="disabled")
            
            # 更新行号
            self.line_numbers.config(state="normal")
            self.line_numbers.delete("1.0", "end")
            lines = content.split('\n')
            line_numbers = '\n'.join(f"{i+1:4d}" for i in range(len(lines)))
            self.line_numbers.insert("1.0", line_numbers)
            self.line_numbers.config(state="disabled")
            
            # 同步滚动位置
            self.dst_preview.yview_moveto(0)

    def update_stats(self, count_in: int, count_out: int):
        """更新预览统计信息"""
        # 计算匹配率
        match_rate = (count_out / count_in * 100) if count_in > 0 else 0
        
        stats = [
            "预览统计信息:",
            f"读取行数: {count_in}",
            f"匹配行数: {count_out}",
            f"匹配率: {match_rate:.2f}%"
        ]
        
        if hasattr(self, 'current_file'):
            stats.extend([
                "",
                f"当前文件: {self.current_file.name}",
                f"文件大小: {self.current_file.stat().st_size // 1024} KB"
            ])
            
        self._update_system_info('\n'.join(stats))
