"""Embedded terminal widget for the terminal board.

- 一行输入对应一行命令执行，支持 cd；
- 输出支持 ANSI 颜色、加粗、下划线等。
"""

import os
import sys

from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import (
    QFont,
    QFontDatabase,
    QColor,
    QBrush,
    QTextCharFormat,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QLineEdit,
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


class TerminalWidget(QWidget):
    """Line-oriented terminal: output view + single-line input, per-command shell."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Output area ---
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(11)
        fixed_font.setStyleHint(QFont.TypeWriter)
        self._output.setFont(fixed_font)
        self._output.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; "
            "selection-background-color: #264f78;"
        )
        fm = self._output.fontMetrics()
        char_width = (
            fm.horizontalAdvance(" ")
            if hasattr(fm, "horizontalAdvance")
            else fm.width(" ")
        )
        self._output.setTabStopDistance(char_width * 8)
        self._output.document().setDocumentMargin(4)
        self._output.setFrameShape(QFrame.NoFrame)

        # --- Input line ---
        self._input = QLineEdit(self)
        self._input.setFont(fixed_font)
        self._input.setMinimumHeight(32)
        self._input.setFocusPolicy(Qt.StrongFocus)
        self._input.setPlaceholderText("Type command and press Enter…")
        self._input.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; "
            "border-top: 1px solid #333; padding: 4px;"
        )
        self._input.returnPressed.connect(self._on_return_pressed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._output, 1)
        layout.addWidget(self._input, 0)

        # Current working directory for commands
        self._cwd = os.path.expanduser("~")
        # ANSI 输出格式状态
        self._current_char_format = self._default_char_format()

        # 确保输入框能获得焦点（点击终端内容区时也会把焦点给输入框）
        self._output.setFocusPolicy(Qt.ClickFocus)
        self._output.mousePressEvent = self._output_click_focus_input

    def _output_click_focus_input(self, event):
        """Click on output area -> focus input line so user can type."""
        self._input.setFocus()
        super(QPlainTextEdit, self._output).mousePressEvent(event)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _append(self, text: str):
        self._output.moveCursor(self._output.textCursor().End)
        self._output.insertPlainText(text)
        self._output.moveCursor(self._output.textCursor().End)

    def _append_line(self, text: str):
        self._append(text + "\n")

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
                self._current_char_format.setFontWeight(99)
            elif p == 2:
                self._current_char_format.setFontWeight(0)
            elif p == 3:
                self._current_char_format.setFontItalic(True)
            elif p == 4:
                self._current_char_format.setFontUnderline(True)
            elif p == 7:
                self._current_char_format.setForeground(DEFAULT_BG)
                self._current_char_format.setBackground(QBrush(DEFAULT_FG))
            elif p == 22:
                self._current_char_format.setFontWeight(0)
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
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        self._output.moveCursor(self._output.textCursor().End)
        for segment, fmt in self._parse_ansi_and_yield_segments(text):
            if segment:
                self._output.setCurrentCharFormat(fmt)
                self._output.insertPlainText(segment)
        self._output.moveCursor(self._output.textCursor().End)

    def _prompt(self) -> str:
        base = os.path.basename(self._cwd) or self._cwd
        return f"{base}$ "

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _on_return_pressed(self):
        line = self._input.text()
        self._input.clear()
        prompt = self._prompt()
        self._append_line(prompt + line)
        line = line.strip()
        if not line:
            return

        # Handle built-in 'cd' so cwd 能保持
        if line.startswith("cd"):
            self._handle_cd(line)
            return

        self._run_command(line)

    def _handle_cd(self, line: str):
        parts = line.split(maxsplit=1)
        if len(parts) == 1 or not parts[1]:
            target = os.path.expanduser("~")
        else:
            target = os.path.expanduser(parts[1])
            if not os.path.isabs(target):
                target = os.path.join(self._cwd, target)

        if not os.path.isdir(target):
            self._append_line(f"cd: no such directory: {target}")
            return
        self._cwd = os.path.abspath(target)
        self._append_line(f"(cwd) {self._cwd}")

    # ------------------------------------------------------------------
    # Command execution (per-line QProcess)
    # ------------------------------------------------------------------

    def _run_command(self, line: str):
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(self._cwd)

        def on_ready():
            data = proc.readAllStandardOutput()
            if not data:
                return
            try:
                text = bytes(data).decode("utf-8", errors="replace")
            except Exception:
                text = str(data)
            self._append_ansi(text)

        def on_finished(code, status):
            if code != 0:
                self._append_line(f"[exit {code}]")
            proc.deleteLater()

        proc.readyReadStandardOutput.connect(on_ready)
        proc.finished.connect(on_finished)

        if sys.platform == "win32":
            # Run via cmd /C
            proc.start("cmd.exe", ["/C", line])
        else:
            # Use user's shell if available; fallback to /bin/bash
            shell = os.environ.get("SHELL", "/bin/bash")
            if not os.path.isfile(shell):
                shell = "/bin/bash"
            proc.start(shell, ["-lc", line])

    # ------------------------------------------------------------------
    # QWidget
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._input.setFocus)

    def closeEvent(self, event):
        # 所有 per-command QProcess 都有我们作为 parent，Qt 会自动清理
        super().closeEvent(event)
