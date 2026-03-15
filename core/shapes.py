"""Shape classes for the vector drawing board."""

from enum import Enum, auto
from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor


class ShapeType(Enum):
    LINE = auto()
    RECTANGLE = auto()
    CIRCLE = auto()


class Shape:
    """Base class for all drawable shapes."""

    def __init__(self, pen_color: QColor = None, pen_width: int = 2):
        self.pen_color = pen_color or QColor("black")
        self.pen_width = pen_width
        self.selected = False

    def draw(self, painter: QPainter):
        raise NotImplementedError

    def contains(self, point: QPointF) -> bool:
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

    @staticmethod
    def from_dict(data: dict) -> "Shape":
        shape_type = data.get("type")
        if shape_type == ShapeType.LINE.name:
            return Line.from_dict(data)
        elif shape_type == ShapeType.RECTANGLE.name:
            return Rectangle.from_dict(data)
        elif shape_type == ShapeType.CIRCLE.name:
            return Circle.from_dict(data)
        raise ValueError(f"Unknown shape type: {shape_type}")

    def _make_pen(self) -> QPen:
        pen = QPen(self.pen_color, self.pen_width)
        if self.selected:
            pen.setColor(QColor("blue"))
            pen.setWidth(self.pen_width + 1)
        return pen


class Line(Shape):
    """A straight line between two points."""

    def __init__(self, start: QPointF, end: QPointF, pen_color: QColor = None, pen_width: int = 2):
        super().__init__(pen_color, pen_width)
        self.start = start
        self.end = end

    def draw(self, painter: QPainter):
        painter.setPen(self._make_pen())
        painter.drawLine(self.start, self.end)

    def contains(self, point: QPointF) -> bool:
        # Check if point is within a small distance of the line
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return (point - self.start).manhattanLength() < 8
        t = ((point.x() - self.start.x()) * dx + (point.y() - self.start.y()) * dy) / length_sq
        t = max(0, min(1, t))
        proj_x = self.start.x() + t * dx
        proj_y = self.start.y() + t * dy
        dist_x = point.x() - proj_x
        dist_y = point.y() - proj_y
        return (dist_x * dist_x + dist_y * dist_y) < 64  # 8px tolerance

    def to_dict(self) -> dict:
        return {
            "type": ShapeType.LINE.name,
            "x1": self.start.x(),
            "y1": self.start.y(),
            "x2": self.end.x(),
            "y2": self.end.y(),
            "pen_color": self.pen_color.name(),
            "pen_width": self.pen_width,
        }

    @staticmethod
    def from_dict(data: dict) -> "Line":
        return Line(
            start=QPointF(data["x1"], data["y1"]),
            end=QPointF(data["x2"], data["y2"]),
            pen_color=QColor(data.get("pen_color", "#000000")),
            pen_width=data.get("pen_width", 2),
        )


class Rectangle(Shape):
    """An axis-aligned rectangle."""

    def __init__(self, rect: QRectF, pen_color: QColor = None, pen_width: int = 2):
        super().__init__(pen_color, pen_width)
        self.rect = rect

    def draw(self, painter: QPainter):
        painter.setPen(self._make_pen())
        painter.setBrush(QBrush())  # no fill
        painter.drawRect(self.rect)

    def contains(self, point: QPointF) -> bool:
        return self.rect.contains(point)

    def to_dict(self) -> dict:
        return {
            "type": ShapeType.RECTANGLE.name,
            "x": self.rect.x(),
            "y": self.rect.y(),
            "width": self.rect.width(),
            "height": self.rect.height(),
            "pen_color": self.pen_color.name(),
            "pen_width": self.pen_width,
        }

    @staticmethod
    def from_dict(data: dict) -> "Rectangle":
        return Rectangle(
            rect=QRectF(data["x"], data["y"], data["width"], data["height"]),
            pen_color=QColor(data.get("pen_color", "#000000")),
            pen_width=data.get("pen_width", 2),
        )


class Circle(Shape):
    """A circle or ellipse defined by its bounding rectangle."""

    def __init__(self, rect: QRectF, pen_color: QColor = None, pen_width: int = 2):
        super().__init__(pen_color, pen_width)
        self.rect = rect

    def draw(self, painter: QPainter):
        painter.setPen(self._make_pen())
        painter.setBrush(QBrush())  # no fill
        painter.drawEllipse(self.rect)

    def contains(self, point: QPointF) -> bool:
        # Check if point is inside the bounding rectangle
        cx = self.rect.center().x()
        cy = self.rect.center().y()
        rx = self.rect.width() / 2
        ry = self.rect.height() / 2
        if rx == 0 or ry == 0:
            return False
        dx = (point.x() - cx) / rx
        dy = (point.y() - cy) / ry
        return (dx * dx + dy * dy) <= 1.0

    def to_dict(self) -> dict:
        return {
            "type": ShapeType.CIRCLE.name,
            "x": self.rect.x(),
            "y": self.rect.y(),
            "width": self.rect.width(),
            "height": self.rect.height(),
            "pen_color": self.pen_color.name(),
            "pen_width": self.pen_width,
        }

    @staticmethod
    def from_dict(data: dict) -> "Circle":
        return Circle(
            rect=QRectF(data["x"], data["y"], data["width"], data["height"]),
            pen_color=QColor(data.get("pen_color", "#000000")),
            pen_width=data.get("pen_width", 2),
        )
