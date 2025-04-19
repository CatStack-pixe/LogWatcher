import os
import chardet
from pathlib import Path
from typing import Callable, Generator, Optional, Tuple

class FileHandler:
    CHUNK_SIZE = 8192  # 8KB 块大小
    LARGE_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def detect_encoding(file_path: Path) -> str:
        """检测文件编码"""
        with open(file_path, 'rb') as f:
            raw = f.read(4096)  # 读取前4KB用于检测
            result = chardet.detect(raw)
            return result['encoding'] or 'utf-8'

    @staticmethod
    def is_large_file(file_path: Path) -> bool:
        """检查是否是大文件"""
        return file_path.stat().st_size > FileHandler.LARGE_FILE_SIZE

    @staticmethod
    def get_file_size_info(file_path: Path) -> Tuple[float, str]:
        """获取文件大小信息"""
        size = file_path.stat().st_size
        units = ['B', 'KB', 'MB', 'GB']
        unit_index = 0
        while size > 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return size, units[unit_index]

    @staticmethod
    def read_in_chunks(file_path: Path, encoding: str = 'utf-8') -> Generator[str, None, None]:
        """分块读取文件内容"""
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            while True:
                chunk = f.read(FileHandler.CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    @staticmethod
    def process_large_file(
            input_path: Path,
            output_path: Path,
            line_processor: Callable[[str], Optional[str]],
            encoding: str = 'utf-8',
            callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[int, int]:
        """处理大文件，支持进度回调
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            line_processor: 行处理函数
            encoding: 文件编码
            callback: 进度回调函数
            
        Returns:
            处理的总行数和匹配的行数
        """
        total_lines = sum(1 for _ in open(input_path, 'r', encoding=encoding, errors='ignore'))
        count_in = count_out = 0
        
        with open(input_path, 'r', encoding=encoding, errors='ignore') as fin, \
             open(output_path, 'w', encoding=encoding, errors='ignore') as fout:
            
            for line in fin:
                count_in += 1
                result = line_processor(line)
                if result is not None:
                    fout.write(result + '\n')
                    count_out += 1
                    
                if callback and count_in % 1000 == 0:
                    callback(count_in, total_lines)
                    
        return count_in, count_out