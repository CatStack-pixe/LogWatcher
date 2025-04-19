import json
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """配置管理类，用于保存和加载用户配置"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.logwatch'
        self.config_file = self.config_dir / 'config.json'
        self.default_config = {
            'theme': 'litera',
            'window_size': '1500x750',
            'last_directory': str(Path.home()),
            'filters': {
                'keyword': '[CHAT]',
                'filter_fields': '[Render thread/INFO] [net.minecraft.client.gui.components.ChatComponent/]:',
                'ignore_case': True,
                'hide_fields': True,
                'enc_in': 'ANSI',
                'enc_out': 'ANSI'
            }
        }
        self._ensure_config_dir()
        
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self.save_config(self.default_config)
            
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if self.config_file.exists():
                with self.config_file.open('r', encoding='utf-8') as f:
                    return json.load(f)
            return self.default_config
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.default_config
            
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置"""
        try:
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
            
    def update_config(self, key: str, value: Any) -> bool:
        """更新单个配置项"""
        config = self.load_config()
        if '.' in key:
            # 处理嵌套配置项，如 'filters.keyword'
            parts = key.split('.')
            current = config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            config[key] = value
        return self.save_config(config)
        
    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置项值"""
        config = self.load_config()
        if '.' in key:
            parts = key.split('.')
            current = config
            for part in parts:
                if part not in current:
                    return default
                current = current[part]
            return current
        return config.get(key, default)