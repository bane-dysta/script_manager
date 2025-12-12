# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_dynamic_libs
import tkinterdnd2

block_cipher = None

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
        (tkdnd_lib, 'tkinterdnd2/tkdnd'),  # Add tkdnd data files
    ],
    hiddenimports=[
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