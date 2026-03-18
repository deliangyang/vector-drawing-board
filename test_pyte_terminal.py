#!/usr/bin/env python3
"""测试基于 pyte 的终端组件"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui.terminal_widget import TerminalWidget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Pyte Terminal Test")
    window.resize(800, 600)
    
    terminal = TerminalWidget()
    window.setCentralWidget(terminal)
    
    window.show()
    sys.exit(app.exec_())
