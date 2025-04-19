from pathlib import Path
from typing import List, Tuple, Optional
from .file_handler import FileHandler

class LogProcessor:
    def __init__(self, app_instance=None):
        self.app = app_instance
        self.processing_stats = {"total": 0, "matched": 0}
        self.file_handler = FileHandler()

    def filter_log(self, 
                  input_path: Path, 
                  output_path: Optional[Path],
                  keywords: str,
                  ignore_case: bool,
                  read_enc: str = None,
                  write_enc: str = None,
                  filter_fields: str = "",
                  enable_field_filter: bool = False,
                  preview_mode: bool = False) -> Tuple[int, int]:
        """处理单个日志文件"""
        try:
            if not input_path.exists():
                if self.app:
                    self.app.log_error(f"❌ 错误：输入文件不存在：{input_path}")
                return (0, 0)

            # 如果未指定编码，自动检测
            if read_enc == 'auto' or not read_enc:
                read_enc = FileHandler.detect_encoding(input_path)
                if self.app:
                    self.app.log_info(f"📝 检测到文件编码: {read_enc}")

            # 如果是预览模式，使用相同的编码
            if preview_mode:
                write_enc = read_enc
            elif not write_enc:
                write_enc = read_enc

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # 分割关键字和过滤字段
            keyword_list = [k.strip() for k in keywords.split('|') if k.strip()]
            fields_to_filter = [field.strip() for field in filter_fields.split('|') if field.strip()]

            def process_line(line: str) -> Optional[str]:
                """处理单行文本"""
                hay = line.lower() if ignore_case else line
                if any(k.lower() in hay if ignore_case else k in hay for k in keyword_list):
                    # 处理\n字符进行转义换行
                    processed_line = line.replace('\\n', '\n')
                    
                    if enable_field_filter and fields_to_filter:
                        for field in fields_to_filter:
                            field_pattern = field.lower() if ignore_case else field
                            hay = processed_line.lower() if ignore_case else processed_line
                            if field_pattern in hay:
                                start_idx = hay.find(field_pattern)
                                if start_idx >= 0:
                                    end_idx = start_idx + len(field)
                                    while end_idx < len(processed_line) and processed_line[end_idx] in ' :|\t':
                                        end_idx += 1
                                    processed_line = processed_line[:start_idx] + processed_line[end_idx:]
                    return processed_line
                return None

            # 检查是否是大文件
            is_large = FileHandler.is_large_file(input_path)
            if is_large and self.app:
                size, unit = FileHandler.get_file_size_info(input_path)
                self.app.log_info(f"📦 处理大文件: {size:.2f} {unit}")

            # 处理进度回调
            def on_progress(current: int, total: int):
                if self.app:
                    percent = (current / total) * 100 if total > 0 else 0
                    self.app.update_progress(f"处理进度: {current}/{total} 行 ({percent:.1f}%)")

            # 处理文件
            if preview_mode and self.app:
                content = []
                count_in = count_out = 0
                for chunk in FileHandler.read_in_chunks(input_path, read_enc):
                    for line in chunk.splitlines():
                        count_in += 1
                        result = process_line(line)
                        if result is not None:
                            content.append(result)
                            count_out += 1
                
                preview_content = '\n'.join(content)
                self.app.update_preview_content(preview_content)
                if keyword_list:  # 只有在有关键字的情况下才进行高亮
                    self.app._highlight_keywords(keyword_list, ignore_case)
                
                # 更新统计信息
                self.app._update_system_info(f"预览统计:\n读取: {count_in} 行\n匹配: {count_out} 行")
                return (count_in, count_out)
            else:
                # 正常处理模式
                return FileHandler.process_large_file(
                    input_path,
                    output_path,
                    process_line,
                    encoding=read_enc,
                    callback=on_progress if is_large else None
                )

        except LookupError:
            if self.app:
                self.app.log_error(f"❌ 错误：不支持的编码 '{read_enc}' 或 '{write_enc}'")
        except Exception as e:
            if self.app:
                self.app.log_error(f"❌ 处理出错 {input_path.name}: {e}")
        return (0, 0)

    def batch_process(self, files: List[Path], output_dir: Path, **kwargs) -> None:
        """批量处理多个文件"""
        try:
            total_files = len(files)
            self.processing_stats = {"total": 0, "matched": 0}  # 重置统计信息
            
            for i, input_path in enumerate(files, 1):
                if self.app:
                    self.app.log_info(f"📄 处理文件 ({i}/{total_files}): {input_path.name}")
                
                output_path = output_dir / f"{input_path.stem}_filtered{input_path.suffix}"
                count_in, count_out = self.filter_log(input_path, output_path, **kwargs)
                
                # 更新统计信息
                if count_in > 0:
                    self.processing_stats["total"] += count_in
                    self.processing_stats["matched"] += count_out
                    
            # 处理完成后的汇总信息
            if self.app and self.processing_stats["total"] > 0:
                percent = (self.processing_stats['matched'] / self.processing_stats['total'] * 100)
                self.app.log_info(f"\n✅ 批量处理完成")
                self.app.log_info(f"   - 总行数: {self.processing_stats['total']}")
                self.app.log_info(f"   - 匹配行数: {self.processing_stats['matched']}")
                self.app.log_info(f"   - 匹配率: {percent:.2f}%")
                
        except Exception as e:
            if self.app:
                self.app.log_error(f"❌ 批量处理出错: {e}")