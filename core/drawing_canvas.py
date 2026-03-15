"""Drawing canvas widget for the vector drawing board."""

from enum import Enum
from typing import List, Optional

from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtWidgets import QWidget

from core.shapes import Shape, ShapeType, Line, Rectangle, Circle


class Tool(str, Enum):
    """Drawing tool identifiers."""
    SELECT = "select"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"


class DrawingCanvas(QWidget):
    """Interactive canvas widget for drawing vector shapes."""

    shapes_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.shapes: List[Shape] = []
        self.current_tool: str = Tool.LINE
        self.current_color: QColor = QColor("black")
        self.current_pen_width: int = 2
        self._drawing: bool = False
        self._start_point: Optional[QPointF] = None
        self._current_point: Optional[QPointF] = None
        self._selected_shape: Optional[Shape] = None

        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: white;")
        self.setAttribute(Qt.WA_StaticContents)

    # ------------------------------------------------------------------
    # Tool / style setters
    # ------------------------------------------------------------------

    def set_tool(self, tool: str):
        self._clear_selection()
        self.current_tool = tool

    def set_color(self, color: QColor):
        self.current_color = color

    def set_pen_width(self, width: int):
        self.current_pen_width = width

    # ------------------------------------------------------------------
    # Undo / clear
    # ------------------------------------------------------------------

    def undo(self):
        if self.shapes:
            self.shapes.pop()
            self.shapes_changed.emit()
            self.update()

    def clear(self):
        self.shapes.clear()
        self._clear_selection()
        self.shapes_changed.emit()
        self.update()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def shapes_to_dict(self) -> dict:
        return {"shapes": [s.to_dict() for s in self.shapes]}

    def shapes_from_dict(self, data: dict):
        self.shapes = [Shape.from_dict(d) for d in data.get("shapes", [])]
        self._clear_selection()
        self.shapes_changed.emit()
        self.update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_selection(self):
        if self._selected_shape:
            self._selected_shape.selected = False
            self._selected_shape = None

    def _make_rect(self, p1: QPointF, p2: QPointF) -> QRectF:
        """Return a normalised QRectF from two corner points."""
        return QRectF(
            min(p1.x(), p2.x()),
            min(p1.y(), p2.y()),
            abs(p2.x() - p1.x()),
            abs(p2.y() - p1.y()),
        )

    def _build_preview_shape(self) -> Optional[Shape]:
        """Build a temporary preview shape during mouse drag."""
        if self._start_point is None or self._current_point is None:
            return None
        if self.current_tool == Tool.LINE:
            return Line(self._start_point, self._current_point,
                        self.current_color, self.current_pen_width)
        if self.current_tool == Tool.RECTANGLE:
            return Rectangle(self._make_rect(self._start_point, self._current_point),
                             self.current_color, self.current_pen_width)
        if self.current_tool == Tool.CIRCLE:
            return Circle(self._make_rect(self._start_point, self._current_point),
                          self.current_color, self.current_pen_width)
        return None

    # ------------------------------------------------------------------
    # Qt event handlers
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = QPointF(event.pos())
        if self.current_tool == Tool.SELECT:
            self._clear_selection()
            # Iterate in reverse to select the topmost shape
            for shape in reversed(self.shapes):
                if shape.contains(pos):
                    shape.selected = True
                    self._selected_shape = shape
                    break
            self.update()
        else:
            self._drawing = True
            self._start_point = pos
            self._current_point = pos

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._current_point = QPointF(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._drawing:
            return
        self._drawing = False
        self._current_point = QPointF(event.pos())
        shape = self._build_preview_shape()
        if shape is not None:
            self.shapes.append(shape)
            self.shapes_changed.emit()
        self._start_point = None
        self._current_point = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # White background
        painter.fillRect(self.rect(), QBrush(QColor("white")))

        # Draw committed shapes
        for shape in self.shapes:
            shape.draw(painter)

        # Draw live preview
        if self._drawing:
            preview = self._build_preview_shape()
            if preview:
                pen = QPen(self.current_color, self.current_pen_width, Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(QBrush())
                preview.draw(painter)
