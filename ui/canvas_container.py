"""Container that holds the drawing canvas and terminal cards on the canvas."""

from PyQt5.QtCore import QRect, Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy

from core.drawing_canvas import DrawingCanvas
from ui.terminal_card import TerminalCard


class CanvasContainer(QWidget):
    """Widget that contains the drawing canvas and terminal cards laid out on it."""

    terminal_count_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._canvas = DrawingCanvas(self)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.show()
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # List of { "card": TerminalCard, "lx", "ly", "lw", "lh" } in logical coords
        self._terminals = []
        self._terminal_counter = 0

        self._sync_size_from_canvas()

    @property
    def canvas(self) -> DrawingCanvas:
        return self._canvas

    def _sync_size_from_canvas(self):
        """Update container size to match canvas (e.g. after zoom)."""
        self.setMinimumSize(self._canvas.minimumSize())
        self.resize(self._canvas.size())
        self._canvas.setGeometry(0, 0, self._canvas.width(), self._canvas.height())
        zoom = self._canvas.zoom_factor()
        for t in self._terminals:
            card = t["card"]
            lx, ly, lw, lh = t["lx"], t["ly"], t["lw"], t["lh"]
            card.setGeometry(
                int(lx * zoom),
                int(ly * zoom),
                int(lw * zoom),
                int(lh * zoom),
            )
            card.raise_()

    def _on_zoom_changed(self, zoom: float):
        self._sync_size_from_canvas()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep canvas at top-left with its fixed size when container is resized by scroll area
        self._canvas.setGeometry(0, 0, self._canvas.width(), self._canvas.height())

    def add_terminal(self):
        """Add a new terminal card on the canvas with spaced grid layout."""
        self._terminal_counter += 1
        title = f"Terminal {self._terminal_counter}"
        lw, lh = 380, 220
        gap = 28
        cols = 2
        n = len(self._terminals)
        col = n % cols
        row = n // cols
        lx = 50 + col * (lw + gap)
        ly = 50 + row * (lh + gap)
        zoom = self._canvas.zoom_factor()
        card = TerminalCard(title, self)
        card.setGeometry(
            int(lx * zoom),
            int(ly * zoom),
            int(lw * zoom),
            int(lh * zoom),
        )
        card.geometry_changed.connect(self._on_card_geometry_changed)
        card.closed.connect(self._on_card_closed)
        card.show()
        card.raise_()
        self._terminals.append({
            "card": card,
            "lx": lx,
            "ly": ly,
            "lw": lw,
            "lh": lh,
        })
        self.terminal_count_changed.emit(len(self._terminals))

    def _on_card_geometry_changed(self, rect: QRect):
        """Update stored logical rect from card's new geometry (in pixel coords)."""
        zoom = self._canvas.zoom_factor()
        if zoom <= 0:
            return
        for t in self._terminals:
            if t["card"] == self.sender():
                t["lx"] = rect.x() / zoom
                t["ly"] = rect.y() / zoom
                t["lw"] = rect.width() / zoom
                t["lh"] = rect.height() / zoom
                break

    def _on_card_closed(self):
        card = self.sender()
        for i, t in enumerate(self._terminals):
            if t["card"] is card:
                self._terminals.pop(i)
                self.terminal_count_changed.emit(len(self._terminals))
                break

    def close_all_terminals(self):
        """Kill all terminal processes so the app can exit cleanly."""
        for t in list(self._terminals):
            card = t["card"]
            tw = card.terminal_widget()
            if tw:
                tw.kill_process()
        for t in list(self._terminals):
            t["card"].close()
        self._terminals.clear()
        self.terminal_count_changed.emit(0)
