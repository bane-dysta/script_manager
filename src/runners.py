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

    def run(self, arguments="", working_dir="", show_output=True, interactive=False, capture_output=True):
        """运行脚本。

        - show_output=False: 静默运行，不弹出内置窗口或终端窗口。
        - show_output=True 且 interactive=False: 使用内置输出窗口。
        - show_output=True 且 interactive=True 且 capture_output=True: 使用内置交互窗口。
        - show_output=True 且 interactive=True 且 capture_output=False: 打开系统终端交互运行。
        """
        cmd = self.prepare_command(arguments, working_dir)

        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])

        if not show_output:
            return self._run_hidden(cmd, working_dir)

        if interactive and not capture_output:
            return self._run_in_terminal(cmd, working_dir)

        return self._run_captured(cmd, working_dir, interactive)

    def _build_hidden_startup(self):
        """返回隐藏窗口所需的 startupinfo 和 creationflags。"""
        startupinfo = None
        creationflags = 0

        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        return startupinfo, creationflags

    def _run_captured(self, cmd, working_dir, interactive):
        """捕获标准输出/错误，供内置输出窗口显示。"""
        startupinfo, creationflags = self._build_hidden_startup()

        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if interactive else None,
            text=True,
            errors="replace",
            bufsize=1,
            cwd=working_dir,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

    def _run_hidden(self, cmd, working_dir):
        """静默运行，不显示终端，也不捕获到内置窗口。"""
        startupinfo, creationflags = self._build_hidden_startup()

        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=None,
            text=True,
            errors="replace",
            bufsize=1,
            cwd=working_dir,
            startupinfo=startupinfo,
            creationflags=creationflags,
        )

    def _run_in_terminal(self, cmd, working_dir):
        """直接在系统终端中运行脚本，不捕获输出。"""
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        return subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=None,
            stderr=None,
            stdin=None,
            shell=False,
            creationflags=creationflags,
        )


class PythonRunner(ScriptRunner):
    """Python脚本运行器"""

    def prepare_command(self, arguments, working_dir):
        env = next(
            (
                env
                for env in self.config.get("python_environments", [])
                if env.get("name") == self.script_info.get("env")
            ),
            None,
        )
        if not env:
            raise ValueError("找不到指定的Python环境")

        cmd = [env["path"], self.script_info["path"]]
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd


class BatchRunner(ScriptRunner):
    """批处理脚本运行器"""

    def prepare_command(self, arguments, working_dir):
        if os.name == 'nt':
            cmd = ['cmd', '/c', self.script_info["path"]]
        else:
            cmd = [self.script_info["path"]]

        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd


class ExecutableRunner(ScriptRunner):
    """可执行文件运行器"""

    def prepare_command(self, arguments, working_dir):
        cmd = [self.script_info["path"]]
        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd

    def run(self, arguments="", working_dir="", show_output=False, interactive=False, capture_output=False):
        """可执行文件保持原样直接启动。"""
        cmd = self.prepare_command(arguments, working_dir)

        if not working_dir:
            working_dir = os.path.dirname(self.script_info["path"])

        return subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=None,
            stderr=None,
            stdin=None,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
        )


class PowerShellRunner(ScriptRunner):
    """PowerShell脚本运行器"""

    def prepare_command(self, arguments, working_dir):
        if os.name == 'nt':
            cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass']
        else:
            cmd = ['pwsh', '-NoProfile']

        cmd.extend(['-File', self.script_info["path"]])

        if arguments:
            cmd.extend(split_arguments(arguments))
        return cmd


class RunnerFactory:
    """运行器工厂类"""

    _runners = {
        "python": PythonRunner,
        "batch": BatchRunner,
        "powershell": PowerShellRunner,
        "executable": ExecutableRunner,
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
