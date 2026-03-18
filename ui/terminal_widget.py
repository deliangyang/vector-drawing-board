"""Embedded real terminal widget with PTY support using pyte.

真实的终端模拟器，使用 pyte 进行终端仿真，正确处理 ANSI 序列和光标位置。
"""

import os
import sys
import pty
import signal
import struct
import fcntl
import termios

import pyte

from PyQt5.QtCore import Qt, QSocketNotifier, QTimer
from PyQt5.QtGui import (
    QFont,
    QFontDatabase,
    QColor,
    QBrush,
    QTextCharFormat,
    QTextCursor,
    QKeyEvent,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QFrame,
    QApplication,
)

# ANSI 颜色映射
ANSI_COLORS = {
    "black": QColor("#000000"),
    "red": QColor("#cd3131"),
    "green": QColor("#0dbc79"),
    "brown": QColor("#e5e510"),
    "blue": QColor("#2472c8"),
    "magenta": QColor("#bc3fbc"),
    "cyan": QColor("#11a8cd"),
    "white": QColor("#e5e5e5"),
    "brightblack": QColor("#666666"),
    "brightred": QColor("#f14c4c"),
    "brightgreen": QColor("#23d18b"),
    "brightyellow": QColor("#f5f543"),
    "brightblue": QColor("#3b8eea"),
    "brightmagenta": QColor("#d670d6"),
    "brightcyan": QColor("#29b8db"),
    "brightwhite": QColor("#ffffff"),
    "default": QColor("#d4d4d4"),
}

DEFAULT_FG = QColor("#d4d4d4")
DEFAULT_BG = QColor("#1e1e1e")
BASE_FONT_SIZE = 11  # 常规字号


class TerminalWidget(QWidget):
    """Real terminal emulator with PTY support using pyte."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._master_fd = None
        self._pid = None
        self._notifier = None

        # --- Terminal display area ---
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(BASE_FONT_SIZE)
        fixed_font.setStyleHint(QFont.TypeWriter)
        self._text.setFont(fixed_font)
        self._text.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; "
            "selection-background-color: #264f78;"
        )
        fm = self._text.fontMetrics()
        char_width = (
            fm.horizontalAdvance(" ")
            if hasattr(fm, "horizontalAdvance")
            else fm.width(" ")
        )
        self._text.setTabStopDistance(char_width * 8)
        self._text.document().setDocumentMargin(4)
        self._text.setFrameShape(QFrame.NoFrame)
        self._text.setFocusPolicy(Qt.StrongFocus)
        self._text.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._text, 1)

        # Pyte 终端仿真器
        cols, rows = 80, 24
        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.ByteStream(self._screen)
        
        # 缓冲区用于存储不完整的数据
        self._buffer = b""
        
        # 渲染节流定时器
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_screen)
        self._pending_render = False
        
        # 光标闪烁定时器
        self._cursor_visible = True
        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        self._cursor_timer.start(500)  # 500ms 闪烁一次
        
        # 初始工作目录
        self._initial_cwd = None

        # 启动 shell
        QTimer.singleShot(100, self._start_shell)

    def set_initial_cwd(self, cwd: str):
        """设置 shell 启动时的初始工作目录。"""
        self._initial_cwd = cwd
    
    def get_current_cwd(self) -> str:
        """获取 shell 进程的当前工作目录。"""
        if self._pid is None:
            return os.getcwd()
        try:
            # 通过 /proc 读取进程的当前目录
            return os.readlink(f"/proc/{self._pid}/cwd")
        except (OSError, FileNotFoundError):
            return os.getcwd()

    def _start_shell(self):
        """启动真正的 shell 进程（通过 PTY）。"""
        if self._master_fd is not None:
            return

        # 获取终端大小
        cols, rows = self._get_terminal_size()
        
        # 重新创建 screen 以适应窗口大小
        self._screen = pyte.Screen(cols, rows)
        self._stream = pyte.ByteStream(self._screen)
        
        try:
            # 创建 PTY
            self._pid, self._master_fd = pty.fork()
            
            if self._pid == 0:
                # 子进程：执行 shell
                shell = os.environ.get("SHELL", "/bin/bash")
                if not os.path.isfile(shell):
                    shell = "/bin/bash"
                
                # 设置环境变量
                env = os.environ.copy()
                env["TERM"] = "xterm-256color"
                env["COLUMNS"] = str(cols)
                env["LINES"] = str(rows)
                env["PS1"] = "$ "  # 简单的提示符
                
                # 禁用 fish shell 的终端能力查询，避免超时警告
                env["fish_term_256color"] = "1"
                env["fish_query_os_name"] = "0"
                
                # 切换到初始工作目录（如果指定）
                if self._initial_cwd and os.path.isdir(self._initial_cwd):
                    try:
                        os.chdir(self._initial_cwd)
                    except OSError:
                        pass
                
                try:
                    os.execve(shell, [shell, "-i"], env)
                except Exception as e:
                    print(f"Failed to start shell: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                # 父进程：设置 PTY
                self._set_terminal_size(cols, rows)
                
                # 设置为非阻塞模式
                flags = fcntl.fcntl(self._master_fd, fcntl.F_GETFL)
                fcntl.fcntl(self._master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                # 使用 QSocketNotifier 监听 PTY 输出
                self._notifier = QSocketNotifier(
                    self._master_fd, QSocketNotifier.Read, self
                )
                self._notifier.activated.connect(self._read_output)
        except Exception as e:
            self._text.setPlainText(f"Error starting shell: {e}\n")

    def _get_terminal_size(self):
        """根据窗口大小计算终端的列数和行数。"""
        fm = self._text.fontMetrics()
        char_width = (
            fm.horizontalAdvance("M")
            if hasattr(fm, "horizontalAdvance")
            else fm.width("M")
        )
        char_height = fm.height()
        
        viewport = self._text.viewport()
        cols = max(80, viewport.width() // char_width)
        rows = max(24, viewport.height() // char_height)
        
        return cols, rows

    def _set_terminal_size(self, cols, rows):
        """设置 PTY 的终端大小。"""
        if self._master_fd is None:
            return
        
        size = struct.pack("HHHH", rows, cols, 0, 0)
        try:
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, size)
        except Exception:
            pass

    def resizeEvent(self, event):
        """窗口大小改变时，更新 PTY 终端大小。"""
        super().resizeEvent(event)
        if self._master_fd is not None:
            cols, rows = self._get_terminal_size()
            # 调整 screen 大小
            self._screen.resize(rows, cols)
            self._set_terminal_size(cols, rows)
            self._render_screen()

    def set_zoom(self, zoom: float):
        """更新字体大小以适应缩放。"""
        self._zoom = zoom
        font_size = BASE_FONT_SIZE if zoom >= 1.0 else int(BASE_FONT_SIZE * zoom)
        font_size = max(6, font_size)
        
        font = self._text.font()
        font.setPointSize(font_size)
        self._text.setFont(font)
        
        # 更新 tab 宽度
        fm = self._text.fontMetrics()
        char_width = (
            fm.horizontalAdvance(" ")
            if hasattr(fm, "horizontalAdvance")
            else fm.width(" ")
        )
        self._text.setTabStopDistance(char_width * 8)
        
        # 更新终端大小
        if self._master_fd is not None:
            cols, rows = self._get_terminal_size()
            self._screen.resize(rows, cols)
            self._set_terminal_size(cols, rows)
            self._render_screen()

    def _read_output(self):
        """从 PTY 读取输出并显示。"""
        if self._master_fd is None:
            return
        
        try:
            # 读取所有可用数据
            while True:
                try:
                    data = os.read(self._master_fd, 4096)
                    if not data:
                        break
                    self._buffer += data
                except BlockingIOError:
                    break
                except OSError:
                    # PTY 已关闭
                    self._cleanup()
                    return
            
            # 处理缓冲区中的数据
            if self._buffer:
                # 将数据传递给 pyte 流处理
                self._stream.feed(self._buffer)
                self._buffer = b""
                
                # 使用节流渲染（16ms ≈ 60fps）
                if not self._render_timer.isActive():
                    self._render_timer.start(16)
        except Exception as e:
            print(f"Error reading output: {e}", file=sys.stderr)

    def _toggle_cursor(self):
        """切换光标可见状态并触发重新渲染。"""
        self._cursor_visible = not self._cursor_visible
        self._render_screen()
    
    def _render_screen(self):
        """将 pyte screen 渲染到 QPlainTextEdit。"""
        self._text.setReadOnly(False)
        self._text.clear()
        
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        # 获取当前光标位置
        cursor_x = self._screen.cursor.x
        cursor_y = self._screen.cursor.y
        
        # 遍历屏幕的每一行
        for y in range(self._screen.lines):
            line = self._screen.buffer[y]
            
            # 渲染该行的每个字符
            for x in range(self._screen.columns):
                char_data = line[x]
                char = char_data.data
                
                # 创建字符格式
                fmt = QTextCharFormat()
                
                # 检查是否是光标位置
                is_cursor = (x == cursor_x and y == cursor_y and self._cursor_visible)
                
                # 设置前景色
                if char_data.fg != "default":
                    fg_color = ANSI_COLORS.get(char_data.fg, DEFAULT_FG)
                    fmt.setForeground(fg_color)
                else:
                    fmt.setForeground(DEFAULT_FG)
                
                # 设置背景色
                if char_data.bg != "default":
                    bg_color = ANSI_COLORS.get(char_data.bg, DEFAULT_BG)
                    fmt.setBackground(QBrush(bg_color))
                else:
                    fmt.setBackground(QBrush(DEFAULT_BG))
                
                # 设置字体样式
                if char_data.bold:
                    fmt.setFontWeight(QFont.Bold)
                if char_data.italics:
                    fmt.setFontItalic(True)
                if char_data.underscore:
                    fmt.setFontUnderline(True)
                if char_data.reverse:
                    # 反转前景和背景色
                    fg = fmt.foreground().color()
                    bg = fmt.background().color()
                    fmt.setForeground(bg)
                    fmt.setBackground(QBrush(fg))
                
                # 如果是光标位置且光标可见，反转颜色
                if is_cursor:
                    fg = fmt.foreground().color()
                    bg = fmt.background().color()
                    fmt.setForeground(bg)
                    fmt.setBackground(QBrush(fg))
                
                # 插入字符
                cursor.setCharFormat(fmt)
                cursor.insertText(char if char != "\x00" else " ")
            
            # 每行结束后添加换行
            if y < self._screen.lines - 1:
                cursor.insertText("\n")
        
        self._text.setReadOnly(True)
        
        # 滚动到底部
        self._text.moveCursor(QTextCursor.End)
        self._text.ensureCursorVisible()

    def eventFilter(self, obj, event):
        """拦截键盘事件并发送到 PTY。"""
        if obj == self._text and event.type() == event.KeyPress:
            self._handle_key_press(event)
            return True
        return super().eventFilter(obj, event)

    def _handle_key_press(self, event: QKeyEvent):
        """处理键盘输入并发送到 shell。"""
        if self._master_fd is None:
            return
        
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        # 特殊键处理
        data = None
        
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            data = b"\r"
        elif key == Qt.Key_Backspace:
            data = b"\x7f"
        elif key == Qt.Key_Tab:
            data = b"\t"
        elif key == Qt.Key_Escape:
            data = b"\x1b"
        elif key == Qt.Key_Up:
            data = b"\x1b[A"
        elif key == Qt.Key_Down:
            data = b"\x1b[B"
        elif key == Qt.Key_Right:
            data = b"\x1b[C"
        elif key == Qt.Key_Left:
            data = b"\x1b[D"
        elif key == Qt.Key_Home:
            data = b"\x1b[H"
        elif key == Qt.Key_End:
            data = b"\x1b[F"
        elif key == Qt.Key_PageUp:
            data = b"\x1b[5~"
        elif key == Qt.Key_PageDown:
            data = b"\x1b[6~"
        elif key == Qt.Key_Delete:
            data = b"\x1b[3~"
        elif key == Qt.Key_Insert:
            data = b"\x1b[2~"
        elif modifiers & Qt.ControlModifier:
            # Ctrl+字母组合
            if key == Qt.Key_C:
                data = b"\x03"  # Ctrl+C (SIGINT)
            elif key == Qt.Key_D:
                data = b"\x04"  # Ctrl+D
            elif key == Qt.Key_Z:
                data = b"\x1a"  # Ctrl+Z
            elif key == Qt.Key_L:
                data = b"\x0c"  # Ctrl+L (clear screen)
            elif key == Qt.Key_A:
                data = b"\x01"  # Ctrl+A (行首)
            elif key == Qt.Key_E:
                data = b"\x05"  # Ctrl+E (行尾)
            elif key == Qt.Key_K:
                data = b"\x0b"  # Ctrl+K (删除到行尾)
            elif key == Qt.Key_U:
                data = b"\x15"  # Ctrl+U (删除整行)
            elif key == Qt.Key_W:
                data = b"\x17"  # Ctrl+W (删除前一个单词)
            elif key == Qt.Key_R:
                data = b"\x12"  # Ctrl+R (反向搜索)
            elif key == Qt.Key_V:
                # Ctrl+V 或 Ctrl+Shift+V：粘贴剪贴板内容
                clipboard = QApplication.clipboard()
                text = clipboard.text()
                if text:
                    data = text.encode("utf-8")
            elif text and len(text) == 1:
                # 其他 Ctrl+字母组合
                char = text[0].lower()
                if 'a' <= char <= 'z':
                    data = bytes([ord(char) - ord('a') + 1])
                elif char == ' ':
                    data = b"\x00"
        elif text and text.isprintable():
            # 普通可打印字符
            data = text.encode("utf-8")
        
        if data:
            try:
                os.write(self._master_fd, data)
            except (OSError, BrokenPipeError):
                self._cleanup()

    def _cleanup(self):
        """清理 PTY 和子进程。"""
        # 停止光标闪烁定时器
        if self._cursor_timer:
            self._cursor_timer.stop()
        
        if self._notifier:
            self._notifier.setEnabled(False)
            self._notifier.deleteLater()
            self._notifier = None
        
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
        
        if self._pid:
            try:
                os.kill(self._pid, signal.SIGTERM)
                os.waitpid(self._pid, 0)
            except (OSError, ChildProcessError):
                pass
            self._pid = None

    def kill_process(self):
        """强制杀死 shell 进程。"""
        self._cleanup()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._text.setFocus)

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
