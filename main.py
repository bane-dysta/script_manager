import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
# 优先使用项目自带的 src，避免被环境中的同名包覆盖
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 使用绝对导入
from src.script_manager import ScriptManager

def main():
    app = ScriptManager()
    app.run()

if __name__ == "__main__":
    main() 