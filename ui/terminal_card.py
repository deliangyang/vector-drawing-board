"""Draggable, resizable terminal card for placement on the canvas."""

from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.terminal_widget import TerminalWidget


class TerminalCard(QFrame):
    """A terminal panel that can be dragged (by title bar) and resized (by corner handle)."""

    geometry_changed = pyqtSignal(object)  # QRect in parent coords
    closed = pyqtSignal()

    TITLE_HEIGHT = 24
    RESIZE_HANDLE_SIZE = 14
    MIN_WIDTH = 200
    MIN_HEIGHT = 120

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet(
            "TerminalCard { background-color: #2d2d2d; border: 1px solid #555; "
            "border-radius: 4px; }"
        )
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self._title = title
        self._drag_start_pos = None
        self._drag_start_geometry = None
        self._resize_start_geometry = None
        self._resize_start_global = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(self.TITLE_HEIGHT)
        self._title_bar.setStyleSheet(
            "background-color: #3c3c3c; border-bottom: 1px solid #555;"
        )
        self._title_bar.setCursor(Qt.SizeAllCursor)
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(6, 0, 2, 0)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("color: #ddd; font-weight: bold;")
        title_layout.addWidget(self._title_label, 1)
        btn_close = QPushButton("×")
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet(
            "QPushButton { background: transparent; color: #aaa; border: none; } "
            "QPushButton:hover { background: #555; color: #fff; }"
        )
        btn_close.clicked.connect(self._on_close)
        title_layout.addWidget(btn_close)
        layout.addWidget(self._title_bar)

        # Terminal content
        self._terminal = TerminalWidget(self)
        layout.addWidget(self._terminal, 1)

        # Resize handle overlay: we'll handle mouse on the card's bottom-right
        self.setMouseTracking(True)

    def terminal_widget(self):
        return self._terminal

    def set_zoom(self, zoom: float):
        """通知内部终端 widget 更新缩放。"""
        self._terminal.set_zoom(zoom)

    def _on_close(self):
        self.closed.emit()
        self.close()

    def _is_in_title_bar(self, pos: QPoint) -> bool:
        return self._title_bar.geometry().contains(
            self._title_bar.mapFrom(self, pos)
        )

    def _is_in_resize_handle(self, pos: QPoint) -> bool:
        r = self.RESIZE_HANDLE_SIZE
        return pos.x() >= self.width() - r and pos.y() >= self.height() - r

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        pos = event.pos()
        if self._is_in_resize_handle(pos):
            self._resize_start_geometry = self.geometry()
            self._resize_start_global = event.globalPos()
            event.accept()
        elif self._is_in_title_bar(pos):
            self._drag_start_pos = self.pos()
            self._drag_start_geometry = self.geometry()
            self._drag_start_global = event.globalPos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_start_geometry is not None:
            delta = event.globalPos() - self._resize_start_global
            new_w = max(
                self.MIN_WIDTH,
                self._resize_start_geometry.width() + delta.x(),
            )
            new_h = max(
                self.MIN_HEIGHT,
                self._resize_start_geometry.height() + delta.y(),
            )
            self.setGeometry(
                self._resize_start_geometry.x(),
                self._resize_start_geometry.y(),
                int(new_w),
                int(new_h),
            )
            event.accept()
            return
        if self._drag_start_geometry is not None:
            delta = event.globalPos() - self._drag_start_global
            self.move(
                self._drag_start_pos.x() + delta.x(),
                self._drag_start_pos.y() + delta.y(),
            )
            self._drag_start_pos = self.pos()
            self._drag_start_global = event.globalPos()
            event.accept()
            return
        if self._is_in_resize_handle(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        if self._resize_start_geometry is not None or self._drag_start_geometry is not None:
            self.geometry_changed.emit(self.geometry())
        self._resize_start_geometry = None
        self._resize_start_global = None
        self._drag_start_pos = None
        self._drag_start_geometry = None
        self._drag_start_global = None
        super().mouseReleaseEvent(event)
