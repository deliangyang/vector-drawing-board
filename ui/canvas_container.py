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
        self.setStyleSheet("background-color: #000000;")
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
        """Update child geometries when zoom changes."""
        # First position the background canvas; container size will be updated separately
        self._canvas.setGeometry(0, 0, self._canvas.minimumWidth(), self._canvas.minimumHeight())
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
        self._update_container_size()

    def _update_container_size(self):
        """Make container large enough to hold all terminals (effectively infinite canvas)."""
        zoom = self._canvas.zoom_factor()
        # Base size from logical canvas
        base_w = self._canvas.minimumWidth()
        base_h = self._canvas.minimumHeight()
        max_w = base_w
        max_h = base_h
        for t in self._terminals:
            x = (t["lx"] + t["lw"]) * zoom
            y = (t["ly"] + t["lh"]) * zoom
            if x > max_w:
                max_w = x
            if y > max_h:
                max_h = y
        margin = 40
        w = int(max_w + margin)
        h = int(max_h + margin)
        self.setMinimumSize(w, h)
        self.resize(w, h)
        # Stretch background canvas to cover the visible area
        self._canvas.setGeometry(0, 0, w, h)

    def _on_zoom_changed(self, zoom: float):
        self._sync_size_from_canvas()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # If the scroll area made the container bigger, stretch the canvas as well
        self._canvas.setGeometry(0, 0, self.width(), self.height())

    def get_terminal_layout(self):
        """Return list of terminal rects in logical coords for persistence."""
        return [
            {"lx": t["lx"], "ly": t["ly"], "lw": t["lw"], "lh": t["lh"]}
            for t in self._terminals
        ]

    def restore_terminals(self, layout_list):
        """Create terminals at saved positions; if layout_list is empty, create one."""
        if not layout_list:
            self.add_terminal()
            return
        for rect in layout_list:
            self._add_terminal_at(
                rect.get("lx", 50),
                rect.get("ly", 50),
                rect.get("lw", 380),
                rect.get("lh", 220),
            )

    def _add_terminal_at(self, lx: float, ly: float, lw: float, lh: float):
        """Create one terminal card at the given logical rect."""
        self._terminal_counter += 1
        title = f"Terminal {self._terminal_counter}"
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
        self._update_container_size()

    def add_terminal(self):
        """Add a new terminal card on the canvas with spaced grid layout."""
        lw, lh = 380, 220
        gap = 28
        cols = 2
        n = len(self._terminals)
        col = n % cols
        row = n // cols
        lx = 50 + col * (lw + gap)
        ly = 50 + row * (lh + gap)
        self._add_terminal_at(lx, ly, lw, lh)

    def relayout_terminals(self):
        """Re-layout all existing terminals into a neat grid from top-left."""
        if not self._terminals:
            return
        lw, lh = 380, 220
        gap = 28
        cols = 2
        zoom = self._canvas.zoom_factor()
        for index, t in enumerate(self._terminals):
            col = index % cols
            row = index // cols
            lx = 50 + col * (lw + gap)
            ly = 50 + row * (lh + gap)
            t["lx"] = lx
            t["ly"] = ly
            t["lw"] = lw
            t["lh"] = lh
            card = t["card"]
            card.setGeometry(
                int(lx * zoom),
                int(ly * zoom),
                int(lw * zoom),
                int(lh * zoom),
            )
            card.raise_()
        self._update_container_size()

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
        self._update_container_size()

    def _on_card_closed(self):
        card = self.sender()
        for i, t in enumerate(self._terminals):
            if t["card"] is card:
                self._terminals.pop(i)
                self.terminal_count_changed.emit(len(self._terminals))
                break
        self._update_container_size()

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
