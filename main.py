import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

# 使用绝对导入
from src.script_manager import ScriptManager

def main():
    app = ScriptManager()
    app.run()

if __name__ == "__main__":
    main() 