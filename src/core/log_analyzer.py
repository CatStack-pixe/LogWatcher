import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

class LogAnalyzer:
    def __init__(self):
        self.current_file = None
        self.df = None
        self.stats = {}
        
    def analyze_file(self, file_path: Path):
        """分析日志文件并生成统计信息
        
        Args:
            file_path: 日志文件路径
        """
        self.current_file = file_path
        self.df = self._parse_log_file(file_path)
        self._generate_stats()
        
    def _parse_log_file(self, file_path: Path) -> pd.DataFrame:
        """解析日志文件内容
        
        Args:
            file_path: 日志文件路径
            
        Returns:
            包含解析后日志数据的DataFrame
        """
        # 读取日志文件
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 解析日志行
        data = []
        time_pattern = r'\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}'
        level_pattern = r'(DEBUG|INFO|WARNING|ERROR|CRITICAL)'
        
        for line in lines:
            try:
                # 提取时间戳
                time_match = re.search(time_pattern, line)
                if time_match:
                    timestamp = datetime.strptime(time_match.group(), '%Y-%m-%d %H:%M:%S')
                else:
                    continue
                    
                # 提取日志级别
                level_match = re.search(level_pattern, line)
                level = level_match.group() if level_match else 'UNKNOWN'
                
                # 提取消息内容
                message = line[time_match.end():].strip()
                if level_match:
                    message = message[level_match.end():].strip()
                
                data.append({
                    'timestamp': timestamp,
                    'level': level,
                    'message': message
                })
            except Exception:
                continue
                
        return pd.DataFrame(data)
        
    def _generate_stats(self):
        """生成统计信息"""
        if self.df is None:
            return
            
        # 基本统计信息
        self.stats['total_lines'] = len(self.df)
        self.stats['time_range'] = {
            'start': self.df['timestamp'].min(),
            'end': self.df['timestamp'].max()
        }
        
        # 日志级别分布
        level_counts = self.df['level'].value_counts()
        self.stats['level_distribution'] = level_counts.to_dict()
        
        # 按小时统计
        self.df['hour'] = self.df['timestamp'].dt.hour
        hour_counts = self.df['hour'].value_counts().sort_index()
        self.stats['hourly_distribution'] = hour_counts.to_dict()
        
        # 关键词频率分析
        all_words = ' '.join(self.df['message']).split()
        word_freq = Counter(all_words)
        self.stats['word_frequency'] = dict(word_freq.most_common(20))
        
    def get_stats(self) -> dict:
        """获取统计结果
        
        Returns:
            包含统计信息的字典
        """
        return self.stats
        
    def has_results(self) -> bool:
        """检查是否有分析结果
        
        Returns:
            bool: 是否存在分析结果
        """
        return bool(self.stats)
        
    def get_current_file(self) -> Path:
        """获取当前分析的文件路径
        
        Returns:
            当前文件路径
        """
        return self.current_file
        
    def plot_time_distribution(self) -> plt.Figure:
        """生成时间分布图
        
        Returns:
            matplotlib图形对象
        """
        if self.df is None:
            return None
            
        plt.figure(figsize=(12, 6))
        sns.set_style("whitegrid")
        sns.histplot(data=self.df, x='hour', bins=24)
        plt.title('日志时间分布')
        plt.xlabel('小时')
        plt.ylabel('数量')
        return plt.gcf()
        
    def plot_level_distribution(self) -> plt.Figure:
        """生成日志级别分布饼图
        
        Returns:
            matplotlib图形对象
        """
        if self.df is None:
            return None
            
        plt.figure(figsize=(8, 8))
        level_counts = self.df['level'].value_counts()
        plt.pie(level_counts.values, labels=level_counts.index, autopct='%1.1f%%')
        plt.title('日志级别分布')
        return plt.gcf()