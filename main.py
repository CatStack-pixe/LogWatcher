import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.gui.main_window import LogFilterGUI

def main():
    app = LogFilterGUI()
    app.mainloop()

if __name__ == "__main__":
    main()