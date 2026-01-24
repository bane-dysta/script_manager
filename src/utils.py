import os
import shlex
import subprocess
from pathlib import Path


def split_arguments(arg_string: str):
    """将命令行参数字符串拆分为参数列表。

    - Linux/macOS: 使用 POSIX 规则解析（支持引号、转义）
    - Windows: 使用非 POSIX 规则解析，避免把反斜杠当作转义符导致路径被破坏

    注意：Windows 下 shlex.split(posix=False) 会保留引号，这里会做一层轻量清理。
    """
    if not arg_string:
        return []

    # Windows 的反斜杠路径在 POSIX 模式下会被当作转义符，导致 `C:\temp` 解析成 `C:temp`
    posix = os.name != "nt"
    parts = shlex.split(arg_string, posix=posix)

    # shlex 在 posix=False 时会保留引号，简单去掉包裹型引号
    if not posix:
        cleaned = []
        for p in parts:
            if len(p) >= 2 and p[0] == p[-1] and p[0] in ("\"", "'"):
                cleaned.append(p[1:-1])
            else:
                cleaned.append(p)
        parts = cleaned

    return parts

def get_python_info(python_path):
    """获取Python环境信息"""
    try:
        # 获取Python版本
        version_result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True
        )
        # 有些环境会把版本输出到 stderr
        version = (version_result.stdout or version_result.stderr).strip()
        
        # 获取已安装的包列表
        pip_result = subprocess.run(
            [python_path, "-m", "pip", "list"],
            capture_output=True,
            text=True
        )
        packages = (pip_result.stdout or pip_result.stderr).strip()
        
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