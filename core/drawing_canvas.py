"""Canvas background widget for the terminal board (zoom only, no drawing)."""

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QWheelEvent
from PyQt5.QtWidgets import QWidget

# Logical size of the canvas
CANVAS_LOGICAL_WIDTH = 600
CANVAS_LOGICAL_HEIGHT = 400
ZOOM_MIN = 0.25
ZOOM_MAX = 3.0
ZOOM_STEP = 0.25


class DrawingCanvas(QWidget):
    """Canvas widget: background only, supports zoom (for terminal layout)."""

    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_factor: float = 1.0

        self._update_zoom_size()
        self.setStyleSheet("background-color: #252526;")
        self.setAttribute(Qt.WA_StaticContents)

    def _update_zoom_size(self):
        w = max(1, int(CANVAS_LOGICAL_WIDTH * self._zoom_factor))
        h = max(1, int(CANVAS_LOGICAL_HEIGHT * self._zoom_factor))
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def zoom_factor(self) -> float:
        return self._zoom_factor

    def set_zoom_factor(self, factor: float):
        self._zoom_factor = max(ZOOM_MIN, min(ZOOM_MAX, factor))
        self._update_zoom_size()
        self.zoom_changed.emit(self._zoom_factor)
        self.update()

    def zoom_in(self):
        self.set_zoom_factor(self._zoom_factor + ZOOM_STEP)

    def zoom_out(self):
        self.set_zoom_factor(self._zoom_factor - ZOOM_STEP)

    def zoom_reset(self):
        self.set_zoom_factor(1.0)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        logical_rect = QRectF(0, 0, CANVAS_LOGICAL_WIDTH, CANVAS_LOGICAL_HEIGHT)
        painter.save()
        painter.scale(self._zoom_factor, self._zoom_factor)
        painter.fillRect(logical_rect, QBrush(QColor("#252526")))
        painter.restore()
