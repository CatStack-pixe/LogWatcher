from pathlib import Path
from typing import List, Dict
import json
from datetime import datetime

class RecentFiles:
    """最近使用文件管理器"""
    def __init__(self, config_dir: Path, max_items: int = 10):
        self.config_dir = config_dir
        self.max_items = max_items
        self.recent_file = config_dir / 'recent_files.json'
        self._ensure_file()
        
    def _ensure_file(self):
        """确保配置文件存在"""
        if not self.recent_file.exists():
            self.save_files([])
            
    def load_files(self) -> List[Dict]:
        """加载最近使用的文件列表"""
        try:
            with self.recent_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
            
    def save_files(self, files: List[Dict]):
        """保存最近使用的文件列表"""
        try:
            with self.recent_file.open('w', encoding='utf-8') as f:
                json.dump(files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存最近文件列表失败: {e}")
            
    def add_file(self, file_path: Path):
        """添加文件到最近使用列表"""
        if not file_path.exists():
            return
            
        files = self.load_files()
        
        # 创建新的文件记录
        new_file = {
            'path': str(file_path),
            'name': file_path.name,
            'last_accessed': datetime.now().isoformat(),
            'size': file_path.stat().st_size
        }
        
        # 移除已存在的同名文件
        files = [f for f in files if f['path'] != str(file_path)]
        
        # 添加新文件到列表开头
        files.insert(0, new_file)
        
        # 限制列表长度
        files = files[:self.max_items]
        
        self.save_files(files)
        
    def remove_file(self, file_path: Path):
        """从最近使用列表中移除文件"""
        files = self.load_files()
        files = [f for f in files if f['path'] != str(file_path)]
        self.save_files(files)
        
    def clear_files(self):
        """清空最近使用列表"""
        self.save_files([])
        
    def get_valid_files(self) -> List[Dict]:
        """获取仍然有效的文件列表（存在于磁盘上的文件）"""
        files = self.load_files()
        valid_files = []
        
        for file in files:
            if Path(file['path']).exists():
                valid_files.append(file)
                
        # 如果有无效文件，更新保存
        if len(valid_files) != len(files):
            self.save_files(valid_files)
            
        return valid_files