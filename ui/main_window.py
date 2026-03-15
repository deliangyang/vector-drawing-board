"""Main window: terminal board only (no drawing)."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSpinBox,
    QStatusBar,
    QToolBar,
)

from core.drawing_canvas import ZOOM_MIN, ZOOM_MAX, ZOOM_STEP
from ui.canvas_container import CanvasContainer


class MainWindow(QMainWindow):
    """Application window: canvas with terminal cards only."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terminal Board")
        self.resize(1000, 700)

        self._container = CanvasContainer()
        self._canvas = self._container.canvas
        self._canvas.zoom_changed.connect(self._on_canvas_zoom_changed)
        self._container.terminal_count_changed.connect(self._on_terminal_count_changed)

        scroll = QScrollArea()
        scroll.setWidget(self._container)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._build_zoom_toolbar()

    def _build_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menu_bar.addMenu("&View")
        act_zoom_in = QAction("Zoom &In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(self._canvas.zoom_in)
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom &Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._canvas.zoom_out)
        view_menu.addAction(act_zoom_out)

        act_zoom_reset = QAction("Reset &100%", self)
        act_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom_reset.triggered.connect(self._canvas.zoom_reset)
        view_menu.addAction(act_zoom_reset)

        view_menu.addSeparator()
        act_add_terminal = QAction("Add &Terminal", self)
        act_add_terminal.setShortcut(QKeySequence("Ctrl+Shift+T"))
        act_add_terminal.triggered.connect(self._container.add_terminal)
        view_menu.addAction(act_add_terminal)

    def _build_toolbar(self):
        toolbar = QToolBar("Main", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        act_add_terminal = QAction("Add Terminal", self)
        act_add_terminal.setShortcut(QKeySequence("Ctrl+Shift+T"))
        act_add_terminal.triggered.connect(self._container.add_terminal)
        toolbar.addAction(act_add_terminal)

    def _build_zoom_toolbar(self):
        zoom_toolbar = QToolBar("Zoom", self)
        zoom_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(Qt.TopToolBarArea, zoom_toolbar)

        act_zoom_in = QAction("Zoom In", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        act_zoom_in.triggered.connect(self._canvas.zoom_in)
        zoom_toolbar.addAction(act_zoom_in)

        act_zoom_out = QAction("Zoom Out", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(self._canvas.zoom_out)
        zoom_toolbar.addAction(act_zoom_out)

        act_zoom_reset = QAction("100%", self)
        act_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        act_zoom_reset.triggered.connect(self._canvas.zoom_reset)
        zoom_toolbar.addAction(act_zoom_reset)

        zoom_toolbar.addWidget(QLabel("  Scale: "))
        self._spin_zoom = QSpinBox()
        self._spin_zoom.setRange(int(ZOOM_MIN * 100), int(ZOOM_MAX * 100))
        self._spin_zoom.setValue(100)
        self._spin_zoom.setSuffix("%")
        self._spin_zoom.valueChanged.connect(self._on_zoom_spin_changed)
        zoom_toolbar.addWidget(self._spin_zoom)

        self._canvas.set_zoom_factor(1.0)

    def _build_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._label_terminals = QLabel("Terminals: 0")
        self._status_bar.addWidget(self._label_terminals, 1)

    def _on_zoom_spin_changed(self, value: int):
        factor = value / 100.0
        if abs(self._canvas.zoom_factor() - factor) > 0.001:
            self._canvas.set_zoom_factor(factor)

    def _on_canvas_zoom_changed(self, factor: float):
        v = int(round(factor * 100))
        if self._spin_zoom.value() != v:
            self._spin_zoom.blockSignals(True)
            self._spin_zoom.setValue(v)
            self._spin_zoom.blockSignals(False)

    def _on_terminal_count_changed(self, count: int):
        self._label_terminals.setText(f"Terminals: {count}")

    def closeEvent(self, event):
        self._container.close_all_terminals()
        event.accept()
