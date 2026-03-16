"""Embedded real terminal widget with PTY support.

真实的终端模拟器，支持交互式程序（vim, htop, python REPL等）。
"""

import os
import sys
import pty
import signal
import struct
import fcntl
import termios

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
)

# ANSI 颜色（深色背景）
ANSI_FG = [
    QColor("#000000"), QColor("#cd3131"), QColor("#0dbc79"), QColor("#e5e510"),
    QColor("#2472c8"), QColor("#bc3fbc"), QColor("#11a8cd"), QColor("#e5e5e5"),
]
ANSI_FG_BRIGHT = [
    QColor("#666666"), QColor("#f14c4c"), QColor("#23d18b"), QColor("#f5f543"),
    QColor("#3b8eea"), QColor("#d670d6"), QColor("#29b8db"), QColor("#e5e5e5"),
]
ANSI_BG = [
    QColor("#000000"), QColor("#cd3131"), QColor("#0dbc79"), QColor("#e5e510"),
    QColor("#2472c8"), QColor("#bc3fbc"), QColor("#11a8cd"), QColor("#e5e5e5"),
]
DEFAULT_FG = QColor("#d4d4d4")
DEFAULT_BG = QColor("#1e1e1e")
BASE_FONT_SIZE = 11  # 常规字号


class TerminalWidget(QWidget):
    """Real terminal emulator with PTY support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._master_fd = None
        self._pid = None
        self._notifier = None
        self._local_echo = True  # 启用本地回显

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

        # ANSI 格式状态
        self._current_char_format = self._default_char_format()
        
        # 缓冲区用于存储不完整的 ANSI 序列
        self._buffer = b""

        # 启动 shell
        QTimer.singleShot(100, self._start_shell)

    def _start_shell(self):
        """启动真正的 shell 进程（通过 PTY）。"""
        if self._master_fd is not None:
            return

        # 获取终端大小
        cols, rows = self._get_terminal_size()
        
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
                env["fish_term_256color"] = "1"  # 告诉 fish 支持 256 色
                env["fish_query_os_name"] = "0"  # 禁用 OS 名称查询
                
                try:
                    os.execve(shell, [shell, "-i"], env)
                except Exception as e:
                    print(f"Failed to start shell: {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                # 父进程：设置 PTY
                self._set_terminal_size(cols, rows)
                
                # 禁用 PTY 的 echo，避免双重回显
                try:
                    attrs = termios.tcgetattr(self._master_fd)
                    # 禁用所有的 echo 标志
                    attrs[3] = attrs[3] & ~(termios.ECHO | termios.ECHOE | termios.ECHOK | termios.ECHONL)
                    termios.tcsetattr(self._master_fd, termios.TCSANOW, attrs)
                except Exception as e:
                    print(f"Warning: Could not disable PTY echo: {e}", file=sys.stderr)
                
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
            self._set_terminal_size(cols, rows)

    def set_zoom(self, zoom: float):
        """更新字体大小以适应缩放，但不超过常规字号。"""
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
            self._set_terminal_size(cols, rows)

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
                try:
                    text = self._buffer.decode("utf-8", errors="replace")
                    self._buffer = b""
                except UnicodeDecodeError:
                    # 缓冲区可能包含不完整的 UTF-8 序列，保留最后几个字节
                    if len(self._buffer) > 10:
                        text = self._buffer[:-4].decode("utf-8", errors="replace")
                        self._buffer = self._buffer[-4:]
                    else:
                        return
                
                self._append_ansi(text)
        except Exception as e:
            print(f"Error reading output: {e}", file=sys.stderr)

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
        display_char = None  # 用于本地回显的字符
        
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            data = b"\r"
            if self._local_echo:
                display_char = "\n"
        elif key == Qt.Key_Backspace:
            data = b"\x7f"
            if self._local_echo:
                # 退格：删除前一个字符
                self._text.setReadOnly(False)
                cursor = self._text.textCursor()
                cursor.movePosition(QTextCursor.End)
                if not cursor.atBlockStart():
                    cursor.deletePreviousChar()
                self._text.setTextCursor(cursor)
                self._text.setReadOnly(True)
        elif key == Qt.Key_Tab:
            data = b"\t"
            # Tab 可能触发补全，先本地显示
            if self._local_echo:
                display_char = "\t"
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
            # Ctrl+字母组合 - 优先处理特定的键码
            if key == Qt.Key_C:
                # 发送中断信号
                data = b"\x03"  # Ctrl+C (SIGINT)
                if self._local_echo:
                    self._text.setReadOnly(False)
                    self._text.insertPlainText("^C")
                    self._text.setReadOnly(True)
            elif key == Qt.Key_D:
                data = b"\x04"  # Ctrl+D
                if self._local_echo:
                    self._text.setReadOnly(False)
                    self._text.insertPlainText("^D")
                    self._text.setReadOnly(True)
            elif key == Qt.Key_Z:
                data = b"\x1a"  # Ctrl+Z
                if self._local_echo:
                    self._text.setReadOnly(False)
                    self._text.insertPlainText("^Z")
                    self._text.setReadOnly(True)
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
            elif text and len(text) == 1:
                # 其他 Ctrl+字母组合
                char = text[0].lower()
                if 'a' <= char <= 'z':
                    # Ctrl+A = 1, Ctrl+B = 2, ..., Ctrl+Z = 26
                    data = bytes([ord(char) - ord('a') + 1])
                elif char == ' ':
                    data = b"\x00"
        elif text and text.isprintable():
            # 普通可打印字符
            data = text.encode("utf-8")
            if self._local_echo:
                display_char = text
        
        # 本地回显（如果启用）
        if display_char:
            # 临时禁用 read-only 以插入文本
            self._text.setReadOnly(False)
            cursor = self._text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._text.setTextCursor(cursor)
            self._text.insertPlainText(display_char)
            cursor = self._text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._text.setTextCursor(cursor)
            self._text.ensureCursorVisible()
            self._text.setReadOnly(True)  # 恢复 read-only
        
        if data:
            try:
                os.write(self._master_fd, data)
                # 立即尝试读取 shell 输出
                QTimer.singleShot(10, self._read_output)
            except (OSError, BrokenPipeError):
                self._cleanup()

    # ------------------------------------------------------------------
    # ANSI 处理
    # ------------------------------------------------------------------

    def _default_char_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(DEFAULT_FG)
        fmt.setBackground(QBrush(DEFAULT_BG))
        return fmt

    def _apply_sgr(self, params: list) -> None:
        """根据 SGR 参数更新当前格式（颜色、加粗等）。"""
        if not params:
            params = [0]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self._current_char_format = self._default_char_format()
            elif p == 1:
                self._current_char_format.setFontWeight(QFont.Bold)
            elif p == 2:
                self._current_char_format.setFontWeight(QFont.Light)
            elif p == 3:
                self._current_char_format.setFontItalic(True)
            elif p == 4:
                self._current_char_format.setFontUnderline(True)
            elif p == 7:
                self._current_char_format.setForeground(DEFAULT_BG)
                self._current_char_format.setBackground(QBrush(DEFAULT_FG))
            elif p == 22:
                self._current_char_format.setFontWeight(QFont.Normal)
            elif p == 23:
                self._current_char_format.setFontItalic(False)
            elif p == 24:
                self._current_char_format.setFontUnderline(False)
            elif p == 27:
                self._current_char_format.setForeground(DEFAULT_FG)
                self._current_char_format.setBackground(QBrush(DEFAULT_BG))
            elif 30 <= p <= 37:
                self._current_char_format.setForeground(ANSI_FG[p - 30])
            elif p == 39:
                self._current_char_format.setForeground(DEFAULT_FG)
            elif 40 <= p <= 47:
                self._current_char_format.setBackground(QBrush(ANSI_BG[p - 40]))
            elif p == 49:
                self._current_char_format.setBackground(QBrush(DEFAULT_BG))
            elif 90 <= p <= 97:
                self._current_char_format.setForeground(ANSI_FG_BRIGHT[p - 90])
            elif 100 <= p <= 107:
                self._current_char_format.setBackground(QBrush(ANSI_FG_BRIGHT[p - 100]))
            i += 1

    def _parse_ansi_and_yield_segments(self, text: str):
        """解析 ANSI 转义，yield (纯文本, QTextCharFormat) 片段。"""
        ESC = "\x1b"
        i = 0
        buf = []
        n = len(text)

        def flush():
            nonlocal buf
            if buf:
                segment = "".join(buf)
                buf = []
                yield segment, QTextCharFormat(self._current_char_format)

        while i < n:
            if text[i] == ESC and i + 1 < n:
                yield from flush()
                if text[i + 1] == "[":
                    i += 2
                    start = i
                    while i < n and text[i] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@`":
                        i += 1
                    if i < n:
                        letter = text[i]
                        params_str = text[start:i]
                        i += 1
                        if letter == "m":
                            parts = params_str.split(";")
                            params = []
                            for part in parts:
                                part = part.lstrip("?")
                                if part == "":
                                    params.append(0)
                                else:
                                    try:
                                        params.append(int(part))
                                    except ValueError:
                                        pass
                            if params:
                                self._apply_sgr(params)
                        elif letter in "ABCDEFGH":
                            # 光标移动等控制序列，这里简单忽略
                            pass
                        elif letter == "J":
                            # 清屏
                            if params_str == "" or params_str == "0":
                                # 清除从光标到屏幕末尾
                                pass
                            elif params_str == "2":
                                # 清除整个屏幕
                                self._text.clear()
                        elif letter == "K":
                            # 清除行
                            pass
                elif text[i + 1] == "]":
                    i += 2
                    while i < n:
                        if text[i] == "\x07":
                            i += 1
                            break
                        if text[i] == ESC and i + 1 < n and text[i + 1] == "\\":
                            i += 2
                            break
                        i += 1
                elif text[i + 1] in "()":
                    i += 3
                else:
                    i += 2
                continue
            buf.append(text[i])
            i += 1
        yield from flush()

    def _append_ansi(self, text: str):
        """追加带 ANSI 颜色/加粗等的输出。"""
        if not text:
            return
            
        # 临时禁用 read-only 以插入文本
        self._text.setReadOnly(False)
        
        # 处理回车和换行
        text = text.replace("\r\n", "\n")
        # 简单处理回车（\r）：移到行首
        lines = text.split("\r")
        
        for idx, line in enumerate(lines):
            if idx > 0:
                # 回车：移动光标到当前行开头
                cursor = self._text.textCursor()
                cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.MoveAnchor)
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
                self._text.setTextCursor(cursor)
            
            # 处理 ANSI 序列并插入文本
            self._text.moveCursor(QTextCursor.End)
            for segment, fmt in self._parse_ansi_and_yield_segments(line):
                if segment:
                    self._text.setCurrentCharFormat(fmt)
                    self._text.insertPlainText(segment)
        
        # 滚动到底部并立即更新显示
        self._text.moveCursor(QTextCursor.End)
        self._text.ensureCursorVisible()
        
        # 恢复 read-only
        self._text.setReadOnly(True)

    # ------------------------------------------------------------------
    # 清理和关闭
    # ------------------------------------------------------------------

    def _cleanup(self):
        """清理 PTY 和子进程。"""
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
