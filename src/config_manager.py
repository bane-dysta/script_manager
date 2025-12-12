import yaml
from pathlib import Path
from datetime import datetime
import shutil
from tkinter import messagebox

class ConfigManager:
    def __init__(self):
        # 配置文件路径
        self.config_path = Path.home() / "script_manager_config.yaml"
        
        # 默认配置
        self.default_config = {
            "version": "1.0",
            "scripts": {
                "其他": []  # 只保留"其他"分类作为默认
            },
            "python_environments": [],
            "settings": {
                "default_category": "其他",
                "default_environment": "",
                "backup_enabled": True,
                "backup_path": str(Path.home() / "script_manager_backups"),
                "window_size": "1000x600",
                "last_directory": str(Path.home()),
                "category_order": []  # 添加分类顺序配置
            }
        }
        
        self.config = None
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            # 创建默认配置文件
            self.config = self.default_config.copy()
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}  # 确保返回字典而不是None
                    
                    # 检查并更新配置版本
                    if "version" not in self.config:
                        self.config["version"] = "1.0"
                        self.migrate_config()
                    
                    # 确保所有必要的字段都存在
                    self.ensure_config_structure()
            except Exception as e:
                messagebox.showerror("错误", f"加载配置文件失败: {str(e)}")
                self.config = self.default_config.copy()
        
        # 确保配置文件包含所有必要的字段
        self.ensure_config_structure()
        self.save_config()
    
    def ensure_config_structure(self):
        """确保配置文件包含所有必要的字段"""
        # 使用默认配置补充缺失的字段
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value.copy() if isinstance(value, dict) else value
            elif isinstance(value, dict):
                # 递归检查嵌套的字典
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config[key]:
                        if isinstance(sub_value, dict):
                            self.config[key][sub_key] = sub_value.copy()
                        else:
                            self.config[key][sub_key] = sub_value
        
        # 为现有脚本添加类型字段
        for category in self.config["scripts"].values():
            for script in category:
                if "script_type" not in script:
                    # 默认设置为python类型
                    script["script_type"] = "python"
    
    def create_example_config(self):
        """创建示例配置"""
        return {
            "version": "1.0",
            "scripts": {
                "常用脚本": [
                    {
                        "name": "示例脚本1",
                        "path": "D:/scripts/example1.py",
                        "category": "常用脚本",
                        "env": "Python 3.8",
                        "description": "这是一个示例脚本",
                        "tags": ["示例", "测试"],
                        "arguments": "--help",
                        "working_dir": "",
                        "shortcut": "Ctrl+1",
                        "script_type": "python"  # 添加脚本类型字段
                    }
                ]
            },
            "python_environments": [
                {
                    "name": "Python 3.8",
                    "path": "C:/Python38/python.exe",
                    "description": "主要开发环境",
                    "packages": ["numpy", "pandas"],
                    "is_default": True
                }
            ],
            "settings": {
                "default_category": "其他",
                "default_environment": "",
                "backup_enabled": True,
                "backup_path": str(Path.home() / "script_manager_backups"),
                "window_size": "1000x600",
                "last_directory": str(Path.home())
            }
        }

    def migrate_config(self):
        """迁移旧版本配置"""
        if "scripts" in self.config and isinstance(self.config["scripts"], list):
            # 将旧版本的脚本列表转换为分类格式
            old_scripts = self.config["scripts"]
            self.config["scripts"] = {
                "常用脚本": [],
                "开发工具": [],
                "数据处理": [],
                "其他": []
            }
            for script in old_scripts:
                script["category"] = "其他"
                self.config["scripts"]["其他"].append(script)

    def save_config(self):
        """保存配置到文件"""
        try:
            # 创建备份
            if self.config.get("settings", {}).get("backup_enabled", True):
                backup_path = Path(self.config.get("settings", {}).get("backup_path", 
                                 str(Path.home() / "script_manager_backups")))
                backup_path.mkdir(parents=True, exist_ok=True)
                backup_file = backup_path / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
                if self.config_path.exists():
                    shutil.copy2(self.config_path, backup_file)
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, sort_keys=False, 
                         default_flow_style=False)
                # 添加配置文件说明
                f.write("\n# 脚本管理器配置文件\n")
                f.write("# 请勿手动修改 version 字段\n")
                f.write("# 更多配置示例请参考 script_manager_example.yaml\n")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {str(e)}") 