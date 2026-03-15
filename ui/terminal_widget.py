"""Embedded terminal widget for the terminal board.

实现目标：
- 交互稳定：一行输入，对应一行命令执行；
- 不再出现字符重复、单词拆行的问题；
- 支持基本的 `cd` 和当前目录保持。
实现方式：每一行命令单独启动一个 shell 进程执行（非长期驻留 shell）。
"""

import os
import sys

from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPlainTextEdit,
    QLineEdit,
    QFrame,
)


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
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            self._append(text)

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
