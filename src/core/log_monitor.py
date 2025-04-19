from pathlib import Path
from typing import Callable, Optional
import queue
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

class LogFileHandler(FileSystemEventHandler):
    """日志文件变化处理器"""
    def __init__(self, callback: Callable[[str], None], file_path: Path):
        self.callback = callback
        self.file_path = file_path
        self.last_position = self.file_path.stat().st_size if self.file_path.exists() else 0
        
    def on_modified(self, event):
        if not isinstance(event, FileModifiedEvent):
            return
            
        if Path(event.src_path) != self.file_path:
            return
            
        try:
            current_size = self.file_path.stat().st_size
            if current_size < self.last_position:
                # 文件被截断，从头开始读取
                self.last_position = 0
                
            if current_size > self.last_position:
                with self.file_path.open('r', encoding='utf-8', errors='ignore') as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    if new_content:
                        self.callback(new_content)
                self.last_position = current_size
                
        except Exception as e:
            print(f"读取文件更新时出错: {e}")

class LogMonitor:
    """实时监控日志文件变化"""
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self.running = False
        self.current_file: Optional[Path] = None
        self.observer: Optional[Observer] = None # type: ignore
        self.handler: Optional[LogFileHandler] = None
        self.queue = queue.Queue()
        
    def start_monitoring(self, file_path: Path):
        """开始监控指定文件"""
        if self.running:
            self.stop_monitoring()
            
        self.current_file = file_path
        self.running = True
        
        # 创建文件处理器和观察者
        self.handler = LogFileHandler(self._on_file_update, file_path)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(file_path.parent), recursive=False)
        self.observer.start()
        
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=1.0)
            self.observer = None
        self.current_file = None
        self.handler = None
        
    def _on_file_update(self, new_content: str):
        """处理文件更新"""
        if not self.running:
            return
            
        self.queue.put(new_content)
        self.callback(new_content)
        
    def get_new_content(self) -> str:
        """获取新的内容"""
        content = []
        while not self.queue.empty():
            content.append(self.queue.get_nowait())
        return ''.join(content)
        
    @property
    def is_monitoring(self) -> bool:
        """是否正在监控"""
        return self.running and self.current_file is not None and self.observer is not None