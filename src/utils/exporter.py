import pandas as pd
from pathlib import Path
import json
from datetime import datetime
import matplotlib.pyplot as plt
from jinja2 import Template

class LogExporter:
    def __init__(self):
        self.html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>日志分析报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .chart { text-align: center; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; border: 1px solid #ddd; }
        th { background-color: #f5f5f5; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>日志分析报告</h1>
            <p>生成时间：{{ generate_time }}</p>
            <p>分析文件：{{ file_name }}</p>
        </div>
        
        <div class="section">
            <h2>基本统计信息</h2>
            <table>
                <tr><th>总行数</th><td>{{ stats.total_lines }}</td></tr>
                <tr><th>开始时间</th><td>{{ stats.time_range.start }}</td></tr>
                <tr><th>结束时间</th><td>{{ stats.time_range.end }}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>日志级别分布</h2>
            <table>
                <tr><th>级别</th><th>数量</th><th>占比</th></tr>
                {% for level, count in stats.level_distribution.items() %}
                <tr>
                    <td>{{ level }}</td>
                    <td>{{ count }}</td>
                    <td>{{ "%.2f%%" % (count / stats.total_lines * 100) }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="section">
            <h2>时间分布</h2>
            <table>
                <tr><th>小时</th><th>数量</th></tr>
                {% for hour, count in stats.hourly_distribution.items() %}
                <tr>
                    <td>{{ hour }}</td>
                    <td>{{ count }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="section">
            <h2>关键词频率（Top 20）</h2>
            <table>
                <tr><th>关键词</th><th>出现次数</th></tr>
                {% for word, freq in stats.word_frequency.items() %}
                <tr>
                    <td>{{ word }}</td>
                    <td>{{ freq }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
'''
    
    def export_html(self, stats: dict, file_path: Path, output_path: Path):
        """导出HTML报告
        
        Args:
            stats: 统计信息字典
            file_path: 分析的日志文件路径
            output_path: 输出文件路径
        """
        template = Template(self.html_template)
        html_content = template.render(
            generate_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            file_name=file_path.name,
            stats=stats
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    def export_excel(self, stats: dict, output_path: Path):
        """导出Excel报告
        
        Args:
            stats: 统计信息字典
            output_path: 输出文件路径
        """
        with pd.ExcelWriter(output_path) as writer:
            # 基本信息
            basic_info = pd.DataFrame([{
                '总行数': stats['total_lines'],
                '开始时间': stats['time_range']['start'],
                '结束时间': stats['time_range']['end']
            }])
            basic_info.to_excel(writer, sheet_name='基本信息', index=False)
            
            # 日志级别分布
            level_df = pd.DataFrame([
                {'级别': k, '数量': v}
                for k, v in stats['level_distribution'].items()
            ])
            level_df.to_excel(writer, sheet_name='日志级别分布', index=False)
            
            # 时间分布
            hour_df = pd.DataFrame([
                {'小时': k, '数量': v}
                for k, v in stats['hourly_distribution'].items()
            ])
            hour_df.to_excel(writer, sheet_name='时间分布', index=False)
            
            # 关键词频率
            word_df = pd.DataFrame([
                {'关键词': k, '频率': v}
                for k, v in stats['word_frequency'].items()
            ])
            word_df.to_excel(writer, sheet_name='关键词频率', index=False)
            
    def export_csv(self, stats: dict, output_dir: Path):
        """导出CSV报告
        
        Args:
            stats: 统计信息字典
            output_dir: 输出目录路径
        """
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出基本信息
        basic_info = pd.DataFrame([{
            '总行数': stats['total_lines'],
            '开始时间': stats['time_range']['start'],
            '结束时间': stats['time_range']['end']
        }])
        basic_info.to_csv(output_dir / 'basic_info.csv', index=False, encoding='utf-8')
        
        # 导出日志级别分布
        level_df = pd.DataFrame([
            {'级别': k, '数量': v}
            for k, v in stats['level_distribution'].items()
        ])
        level_df.to_csv(output_dir / 'level_distribution.csv', index=False, encoding='utf-8')
        
        # 导出时间分布
        hour_df = pd.DataFrame([
            {'小时': k, '数量': v}
            for k, v in stats['hourly_distribution'].items()
        ])
        hour_df.to_csv(output_dir / 'hourly_distribution.csv', index=False, encoding='utf-8')
        
        # 导出关键词频率
        word_df = pd.DataFrame([
            {'关键词': k, '频率': v}
            for k, v in stats['word_frequency'].items()
        ])
        word_df.to_csv(output_dir / 'word_frequency.csv', index=False, encoding='utf-8')