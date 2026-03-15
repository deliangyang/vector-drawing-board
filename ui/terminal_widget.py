"""Embedded terminal widget for the drawing board."""

import os
import sys

from PyQt5.QtCore import Qt, QProcess, QByteArray
from PyQt5.QtGui import QFont, QFontDatabase, QKeyEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit


class TerminalWidget(QWidget):
    """Single terminal instance: runs a shell and displays I/O."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_ready_read)
        self._process.finished.connect(self._on_finished)

        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(False)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        fixed_font.setPointSize(10)
        self._text.setFont(fixed_font)
        self._text.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; "
            "selection-background-color: #264f78;"
        )
        self._text.keyPressEvent = self._key_press_event

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text)

        self._start_shell()
        self._text.setPlaceholderText("Starting shell…")

    def _start_shell(self):
        if sys.platform == "win32":
            self._process.start("cmd.exe", [])
        else:
            # No -i: avoid TTY requirement; shell reads commands from stdin
            self._process.start(
                os.environ.get("SHELL", "/bin/bash"),
                [],
            )

    def _on_ready_read(self):
        data = self._process.readAllStandardOutput()
        if data:
            try:
                text = bytes(data).decode("utf-8", errors="replace")
            except Exception:
                text = str(data)
            self._text.setPlaceholderText("")
            self._text.moveCursor(self._text.textCursor().End)
            self._text.insertPlainText(text)
            self._text.moveCursor(self._text.textCursor().End)

    def _on_finished(self, code, status):
        self._text.appendPlainText(f"\n[Process exited with code {code}]\n")

    def _key_press_event(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._send("\r\n")
            self._echo("\n")
            return
        if key == Qt.Key_Backspace:
            self._send("\b")
            self._backspace()
            return
        if key == Qt.Key_Delete:
            self._send("\x1b[3~")
            return
        if key == Qt.Key_Up:
            self._send("\x1b[A")
            return
        if key == Qt.Key_Down:
            self._send("\x1b[B")
            return
        if key == Qt.Key_Left:
            self._send("\x1b[D")
            return
        if key == Qt.Key_Right:
            self._send("\x1b[C")
            return
        if key == Qt.Key_Home:
            self._send("\x1b[H")
            return
        if key == Qt.Key_End:
            self._send("\x1b[F")
            return
        if key == Qt.Key_Tab:
            self._send("\t")
            self._echo("\t")
            return
        if text:
            self._send(text)
            self._echo(text)
            return
        super(QPlainTextEdit, self._text).keyPressEvent(event)

    def _echo(self, s: str):
        """Echo user input into the display (no TTY so shell doesn't echo)."""
        self._text.moveCursor(self._text.textCursor().End)
        self._text.insertPlainText(s)
        self._text.moveCursor(self._text.textCursor().End)

    def _backspace(self):
        """Remove one character at cursor for backspace."""
        cur = self._text.textCursor()
        if cur.position() > 0:
            cur.deletePreviousChar()
            self._text.setTextCursor(cur)

    def _send(self, s: str):
        if self._process.state() == QProcess.Running:
            self._process.write(QByteArray(s.encode("utf-8")))

    def kill_process(self):
        """Force kill the shell process (for app exit)."""
        if self._process.state() == QProcess.Running:
            try:
                self._process.closeWriteChannel()
            except Exception:
                pass
            self._process.terminate()
            if not self._process.waitForFinished(500):
                self._process.kill()
                self._process.waitForFinished(200)

    def closeEvent(self, event):
        self.kill_process()
        super().closeEvent(event)
