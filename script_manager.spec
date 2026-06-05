# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs
import tkinterdnd2

block_cipher = None


def collect_tcl_tk_data():
    """显式收集 Tcl/Tk 运行时数据，避免打包后缺少 _tk_data/_tcl_data。"""
    datas = []
    seen_destinations = set()

    def add_data(source, destination):
        if not source:
            return
        source_path = Path(source)
        if not source_path.is_dir():
            return
        key = (str(source_path.resolve()), destination)
        if key in seen_destinations:
            return
        datas.append((str(source_path), destination))
        seen_destinations.add(key)

    # 优先从当前 Python 的 Tcl 解释器读取真实路径。
    try:
        import tkinter

        tcl = tkinter.Tcl()
        add_data(tcl.eval("info library"), "_tcl_data")
        try:
            tcl.eval("package require Tk")
            add_data(tcl.eval("set tk_library"), "_tk_data")
        except Exception:
            # 无显示环境或 Tk 未能加载时，继续走下面的目录扫描兜底。
            pass
    except Exception:
        pass

    # Windows 官方 Python 通常在 <python>/tcl/tcl8.x 和 <python>/tcl/tk8.x；
    # Conda/部分发行版可能在 Library/lib 或 lib 下。
    search_roots = [
        Path(sys.base_prefix) / "tcl",
        Path(sys.prefix) / "tcl",
        Path(sys.exec_prefix) / "tcl",
        Path(sys.base_prefix) / "Library" / "lib",
        Path(sys.prefix) / "Library" / "lib",
        Path(sys.exec_prefix) / "Library" / "lib",
        Path(sys.base_prefix) / "lib",
        Path(sys.prefix) / "lib",
        Path(sys.exec_prefix) / "lib",
    ]

    destinations = {destination for _, destination in datas}
    for root in search_roots:
        if not root.is_dir():
            continue
        if "_tcl_data" not in destinations:
            for candidate in sorted(root.glob("tcl*")):
                if candidate.is_dir() and (candidate / "init.tcl").exists():
                    add_data(candidate, "_tcl_data")
                    destinations.add("_tcl_data")
                    break
        if "_tk_data" not in destinations:
            for candidate in sorted(root.glob("tk*")):
                if candidate.is_dir() and (candidate / "tk.tcl").exists():
                    add_data(candidate, "_tk_data")
                    destinations.add("_tk_data")
                    break

    missing = {"_tcl_data", "_tk_data"} - {destination for _, destination in datas}
    if missing:
        raise RuntimeError(
            "未找到 Tcl/Tk 数据目录："
            + ", ".join(sorted(missing))
            + "。请确认构建环境的 Python 已安装/启用 tkinter，并先运行 `python -m tkinter` 测试。"
        )

    return datas


tcl_tk_datas = collect_tcl_tk_data()

# Get tkinterdnd2 path
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)
tkdnd_lib = os.path.join(tkdnd_path, 'tkdnd')

# Collect required DLL files
tkdnd_files = []
for file in os.listdir(tkdnd_lib):
    if file.endswith('.dll') or file.endswith('.tcl'):
        source = os.path.join(tkdnd_lib, file)
        dest = os.path.join('tkinterdnd2', 'tkdnd', file)
        tkdnd_files.append((source, dest))

# Add runtime hook to handle PowerShell window
runtime_hook = os.path.join(os.path.dirname(os.path.abspath('script_manager.spec')), 'ps_hook.py')
with open(runtime_hook, 'w', encoding='utf-8') as f:
    f.write('''# Runtime hook: Modify subprocess.Popen behavior for better PowerShell handling
import subprocess
import os

# Save original Popen
original_popen = subprocess.Popen

# Patch Popen behavior
def patched_popen(*args, **kwargs):
    # Check if it's a PowerShell call
    if args and isinstance(args[0], list) and args[0] and 'powershell' in args[0][0].lower():
        # Ensure window hiding flags are set
        if 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = subprocess.STARTUPINFO()
            kwargs['startupinfo'].dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'].wShowWindow = subprocess.SW_HIDE
        
        # Add CREATE_NO_WINDOW flag to ensure no window is shown
        if os.name == 'nt':
            if 'creationflags' not in kwargs:
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            else:
                kwargs['creationflags'] |= subprocess.CREATE_NO_WINDOW
    
    # Call original Popen
    return original_popen(*args, **kwargs)

# Replace subprocess.Popen
subprocess.Popen = patched_popen
''')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=tkdnd_files,  # Add tkdnd DLL files
    datas=[
        *tcl_tk_datas,  # Add Tcl/Tk runtime data used by tkinter
        (tkdnd_lib, 'tkinterdnd2/tkdnd'),  # Add tkdnd data files
    ],
    hiddenimports=[
        'tkinter',
        '_tkinter',
        'tkinterdnd2',
        'yaml',
        'src.script_manager',
        'src.config_manager',
        'src.dialogs',
        'src.utils'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[runtime_hook],  # Add our runtime hook
    excludes=[
        'matplotlib',
        'notebook',
        'PIL',
        'pandas',
        'numpy',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'IPython',
        'jupyter',
        'test',
        'tests',
        'unittest'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='script_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Ensure this is False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    # Add extra uac_admin option for EXE
    uac_admin=False
)

# Collect all files to dist directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='script_manager'
)