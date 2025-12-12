# 空文件，用于标识这是一个Python包

# 导出主要的类和函数，使它们可以通过 src 包直接访问
from .script_manager import ScriptManager
from .config_manager import ConfigManager
from .dialogs import ScriptConfigDialog, OutputWindow, EnvConfigDialog
from .utils import get_python_info, format_path

__all__ = [
    'ScriptManager',
    'ConfigManager',
    'ScriptConfigDialog',
    'OutputWindow',
    'EnvConfigDialog',
    'get_python_info',
    'format_path'
]
