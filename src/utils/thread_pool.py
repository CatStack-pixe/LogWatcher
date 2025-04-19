import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Any
from queue import Queue
import time

class ThreadPoolManager:
    """线程池管理器"""
    
    def __init__(self, max_workers=None):
        """初始化线程池
        
        Args:
            max_workers: 最大工作线程数，默认为CPU核心数 * 2
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = []
        self.results = Queue()
        self._is_running = False
        
    def submit(self, func: Callable, *args, **kwargs) -> None:
        """提交任务到线程池
        
        Args:
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
        """
        future = self.executor.submit(func, *args, **kwargs)
        self.tasks.append(future)
        
    def map(self, func: Callable, items: List[Any], callback: Callable = None) -> None:
        """并行处理列表中的每一项
        
        Args:
            func: 处理函数
            items: 要处理的项目列表
            callback: 每项处理完成后的回调函数
        """
        self._is_running = True
        
        def _wrapper(item):
            try:
                result = func(item)
                if callback:
                    callback(item, result)
                return result
            except Exception as e:
                return e
                
        futures = [self.executor.submit(_wrapper, item) for item in items]
        self.tasks.extend(futures)
        
    def wait(self, timeout=None) -> bool:
        """等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否所有任务都完成
        """
        start_time = time.time()
        while self.tasks:
            for future in list(self.tasks):
                if future.done():
                    self.tasks.remove(future)
                    try:
                        result = future.result()
                        self.results.put(result)
                    except Exception as e:
                        self.results.put(e)
                        
            if timeout and (time.time() - start_time > timeout):
                return False
                
            if not self.tasks:
                break
                
            time.sleep(0.1)
            
        self._is_running = False
        return True
        
    def get_results(self) -> List[Any]:
        """获取所有任务的结果"""
        results = []
        while not self.results.empty():
            results.append(self.results.get())
        return results
        
    @property
    def is_running(self) -> bool:
        """是否有正在运行的任务"""
        return self._is_running
        
    def shutdown(self, wait=True):
        """关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        self.executor.shutdown(wait=wait)
        self._is_running = False