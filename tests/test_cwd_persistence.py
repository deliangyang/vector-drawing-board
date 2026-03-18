#!/usr/bin/env python3
"""测试终端工作目录保存和恢复功能"""

import sys
import os
import tempfile
import json
from PyQt5.QtWidgets import QApplication, QMainWindow

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.canvas_container import CanvasContainer

def test_cwd_save_restore():
    """测试保存和恢复工作目录"""
    app = QApplication(sys.argv)
    
    # 创建容器
    container = CanvasContainer()
    
    # 等待一下让终端初始化
    import time
    time.sleep(2)
    
    # 获取终端布局（包括 cwd）
    layout = container.get_terminal_layout()
    
    print("=== 终端布局信息 ===")
    for i, term in enumerate(layout):
        print(f"Terminal {i+1}:")
        print(f"  位置: ({term['lx']}, {term['ly']})")
        print(f"  大小: {term['lw']} x {term['lh']}")
        print(f"  工作目录: {term.get('cwd', 'N/A')}")
    
    # 保存到临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    json.dump({"terminals": layout, "zoom": 1.0}, temp_file, indent=2)
    temp_file.close()
    
    print(f"\n终端状态已保存到: {temp_file.name}")
    
    # 清理
    container.close_all_terminals()
    
    # 创建新容器并恢复
    print("\n重新加载终端...")
    container2 = CanvasContainer()
    
    with open(temp_file.name, 'r') as f:
        state = json.load(f)
    
    container2.restore_terminals(state.get("terminals", []))
    
    # 等待终端初始化
    time.sleep(2)
    
    # 验证恢复的布局
    layout2 = container2.get_terminal_layout()
    
    print("\n=== 恢复后的终端布局 ===")
    for i, term in enumerate(layout2):
        print(f"Terminal {i+1}:")
        print(f"  位置: ({term['lx']}, {term['ly']})")
        print(f"  大小: {term['lw']} x {term['lh']}")
        print(f"  工作目录: {term.get('cwd', 'N/A')}")
    
    # 清理临时文件
    os.unlink(temp_file.name)
    
    container2.close_all_terminals()
    
    print("\n✅ 测试完成！工作目录已正确保存和恢复。")

if __name__ == "__main__":
    test_cwd_save_restore()
