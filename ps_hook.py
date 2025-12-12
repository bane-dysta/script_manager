# Runtime hook: Modify subprocess.Popen behavior for better PowerShell handling
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
