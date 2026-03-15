"""Embedded terminal widget for the drawing board."""

import os
import re
import sys

from PyQt5.QtCore import Qt, QProcess, QByteArray, QTimer, QProcessEnvironment
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QKeyEvent,
    QTextCharFormat,
    QBrush,
)
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit

# Default terminal colors (dark background)
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
    """Single terminal instance: runs a shell and displays I/O."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_ready_read)
        self._process.readyReadStandardError.connect(self._on_ready_read)
        self._process.finished.connect(self._on_finished)
        self._process.stateChanged.connect(self._on_state_changed)
        self._process.errorOccurred.connect(self._on_error)

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

        self._text.setPlainText("Starting shell…\n")
        self._current_char_format = self._default_char_format()
        self._start_shell()
        QTimer.singleShot(400, self._ensure_prompt)

    def _default_char_format(self) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(DEFAULT_FG)
        fmt.setBackground(QBrush(DEFAULT_BG))
        return fmt

    def _ensure_prompt(self):
        """If shell is running but still showing startup text, show $ prompt."""
        if self._process.state() == QProcess.Running:
            cur = self._text.toPlainText().strip()
            if not cur or cur == "Starting shell…" or cur.startswith("[Failed"):
                self._text.setPlainText("$ ")
                self._text.moveCursor(self._text.textCursor().End)

    def _start_shell(self):
        self._process.setWorkingDirectory(os.path.expanduser("~"))
        if sys.platform == "win32":
            self._process.start("cmd.exe", [])
        else:
            shell = os.environ.get("SHELL", "/bin/bash")
            if not os.path.isfile(shell):
                shell = "/bin/bash"
            # Run shell inside script(1) PTY so it stays interactive (doesn't exit with code 1)
            if self._start_via_script(shell):
                return
            self._process.start(shell, [])

    def _start_via_script(self, shell: str) -> bool:
        """Start shell in a PTY via script(1); return True if launched."""
        script_path = "/usr/bin/script"
        if not os.path.isfile(script_path):
            return False
        penv = QProcessEnvironment.systemEnvironment()
        penv.insert("SHELL", shell)
        self._process.setProcessEnvironment(penv)
        # macOS: script -q /dev/null (uses $SHELL from env)
        # Linux: script -q -c "shell" /dev/null
        if sys.platform == "darwin":
            self._process.start(script_path, ["-q", "/dev/null"])
        else:
            self._process.start(script_path, ["-q", "-c", shell, "/dev/null"])
        return True

    def _apply_sgr(self, params: list) -> None:
        """Update self._current_char_format from SGR params (e.g. 0, 1, 32, 45)."""
        if not params:
            params = [0]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                self._current_char_format = self._default_char_format()
            elif p == 1:
                self._current_char_format.setFontWeight(99)  # bold
            elif p == 2:
                self._current_char_format.setFontWeight(0)
            elif p == 3:
                self._current_char_format.setFontItalic(True)
            elif p == 4:
                self._current_char_format.setFontUnderline(True)
            elif p == 5 or p == 6:
                pass  # blink, no Qt equivalent
            elif p == 7:
                self._current_char_format.setForeground(QBrush(DEFAULT_BG))
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
        """Parse ANSI escape sequences; yield (plain_text, QTextCharFormat) segments."""
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
                    # CSI
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
                                if part == "":
                                    params.append(0)
                                else:
                                    try:
                                        params.extend(int(x) for x in part.split("?"))
                                    except ValueError:
                                        pass
                            self._apply_sgr(params)
                elif text[i + 1] == "]":
                    # OSC: consume until BEL or ST
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
                    i += 3  # two-byte
                else:
                    i += 2
                continue
            buf.append(text[i])
            i += 1
        yield from flush()

    def _on_ready_read(self):
        data = self._process.readAllStandardOutput()
        if not data:
            data = self._process.readAllStandardError()
        if data:
            try:
                text = bytes(data).decode("utf-8", errors="replace")
            except Exception:
                text = str(data)
            self._text.moveCursor(self._text.textCursor().End)
            for segment, fmt in self._parse_ansi_and_yield_segments(text):
                if segment:
                    self._text.setCurrentCharFormat(fmt)
                    self._text.insertPlainText(segment)
            self._text.moveCursor(self._text.textCursor().End)

    def _on_state_changed(self, state):
        if state == QProcess.Running:
            self._text.setPlainText("$ ")
            self._text.moveCursor(self._text.textCursor().End)

    def _on_error(self, code):
        self._text.setPlainText(f"[Failed to start shell: {code}]\n")

    def _on_finished(self, code, status):
        self._text.moveCursor(self._text.textCursor().End)
        self._text.insertPlainText(f"\n[Process exited with code {code}]\n")

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
