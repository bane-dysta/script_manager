import subprocess
import sys
from pathlib import Path

def get_python_info(python_path):
    """获取Python环境信息"""
    try:
        # 获取Python版本
        version_result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True
        )
        version = version_result.stdout.strip()
        
        # 获取已安装的包列表
        pip_result = subprocess.run(
            [python_path, "-m", "pip", "list"],
            capture_output=True,
            text=True
        )
        packages = pip_result.stdout.strip()
        
        return {
            "version": version,
            "packages": packages
        }
    except Exception as e:
        return {
            "version": "获取失败",
            "packages": f"错误: {str(e)}"
        }

def format_path(path):
    """格式化路径，使其更易读"""
    try:
        return str(Path(path).resolve())
    except:
        return path 