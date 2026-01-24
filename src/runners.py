import os
import subprocess
from abc import ABC, abstractmethod

from src.utils import split_arguments

class ScriptRunner(ABC):
    """脚本运行器基类"""
    
    def __init__(self, script_info, config):
        self.script_info = script_info
        self.config = config
    
    @abstractmethod
    def prepare_command(self, arguments, working_dir):
        """准备运行命令"""
        pass
    
    def run(self, arguments="", working_dir="", show_output=True, interactive=False):
        """运行脚本"""
        cmd = self.prepare_command(arguments, working_dir)
        
        # 准备工作目录
        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])
        
        # 创建启动信息对象
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # 使用subprocess运行脚本
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if show_output else subprocess.DEVNULL,
            stderr=subprocess.PIPE if show_output else subprocess.DEVNULL,
            stdin=subprocess.PIPE if interactive else None,
            text=True,
            errors="replace",
            bufsize=1,
            cwd=working_dir,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        return process

class PythonRunner(ScriptRunner):
    """Python脚本运行器"""
    
    def prepare_command(self, arguments, working_dir):
        # 获取Python环境
        env = next((env for env in self.config["python_environments"] 
                   if env["name"] == self.script_info["env"]), None)
        if not env:
            raise ValueError("找不到指定的Python环境")
        
        # 准备命令
        cmd = [env["path"], self.script_info["path"]]
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd

class BatchRunner(ScriptRunner):
    """批处理脚本运行器"""
    
    def prepare_command(self, arguments, working_dir):
        # 对于批处理文件，我们需要使用完整的命令
        if os.name == 'nt':
            cmd = ['cmd', '/c', self.script_info["path"]]
        else:
            cmd = [self.script_info["path"]]
            
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd
    
    def run(self, arguments="", working_dir="", show_output=False, interactive=False):
        """运行批处理脚本"""
        cmd = self.prepare_command(arguments, working_dir)
        
        # 准备工作目录
        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])
        
        try:
            if show_output:
                # 如果需要显示输出，使用基类的运行方式
                return super().run(arguments, working_dir, show_output, interactive)
            else:
                # 直接运行批处理，不捕获输出
                process = subprocess.Popen(
                    cmd,
                    cwd=working_dir,
                    # 不捕获输出，让程序直接显示自己的窗口
                    stdout=None,
                    stderr=None,
                    stdin=None,
                    shell=False,  # 不需要shell，因为我们已经使用cmd /c
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                return process
        except Exception as e:
            raise

class ExecutableRunner(ScriptRunner):
    """可执行文件运行器"""
    
    def prepare_command(self, arguments, working_dir):
        cmd = [self.script_info["path"]]
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd
    
    def run(self, arguments="", working_dir="", show_output=False, interactive=False):
        """直接运行可执行文件，不捕获输出"""
        cmd = self.prepare_command(arguments, working_dir)
        
        # 准备工作目录
        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])
        
        try:
            # 直接运行程序，不捕获输出
            process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                # 不捕获输出，让程序直接显示自己的窗口
                stdout=None,
                stderr=None,
                stdin=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0  # 在Windows上使用新控制台
            )
            return process
        except Exception as e:
            raise

class PowerShellRunner(ScriptRunner):
    """PowerShell脚本运行器"""
    
    def prepare_command(self, arguments, working_dir):
        if os.name == 'nt':
            cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass']
        else:
            # 在非Windows系统上使用 pwsh（非 Windows 下通常不需要/不支持 -ExecutionPolicy）
            cmd = ['pwsh', '-NoProfile']
        
        # 如果不需要显示输出，添加静默运行参数
        if not self.show_output:
            # -WindowStyle 仅在 Windows PowerShell 中有效
            if os.name == 'nt':
                cmd.extend(['-WindowStyle', 'Hidden'])
            cmd.append('-NonInteractive')
        
        cmd.extend(['-File', self.script_info["path"]])
            
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd
    
    def run(self, arguments="", working_dir="", show_output=False, interactive=False):
        """运行PowerShell脚本"""
        # 保存show_output状态以供prepare_command使用
        self.show_output = show_output
        
        cmd = self.prepare_command(arguments, working_dir)
        
        # 准备工作目录
        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])
        
        try:
            if show_output:
                # 如果需要显示输出，使用基类的运行方式
                return super().run(arguments, working_dir, show_output, interactive)
            else:
                # 直接运行脚本，不捕获输出
                process = subprocess.Popen(
                    cmd,
                    cwd=working_dir,
                    stdout=None,
                    stderr=None,
                    stdin=None,
                    shell=False,
                    # 在Windows上使用CREATE_NO_WINDOW标志，因为我们通过PowerShell参数控制窗口
                    creationflags=0 if os.name == 'nt' else 0
                )
                return process
        except Exception as e:
            raise

# 运行器工厂
class RunnerFactory:
    """运行器工厂类"""
    
    _runners = {
        "python": PythonRunner,
        "batch": BatchRunner,
        "powershell": PowerShellRunner,  # 添加PowerShell运行器
        "executable": ExecutableRunner
    }
    
    @classmethod
    def get_runner(cls, script_type):
        """获取运行器实例"""
        runner_class = cls._runners.get(script_type)
        if not runner_class:
            raise ValueError(f"不支持的脚本类型: {script_type}")
        return runner_class
    
    @classmethod
    def register_runner(cls, script_type, runner_class):
        """注册新的运行器"""
        cls._runners[script_type] = runner_class