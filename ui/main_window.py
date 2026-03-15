"""Main window for the vector drawing board application."""

import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QColorDialog,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSpinBox,
    QStatusBar,
    QToolBar,
    QWidget,
    QScrollArea,
)

from core.drawing_canvas import DrawingCanvas, Tool


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector Drawing Board")
        self.resize(1000, 700)
        self._current_file: str = ""
        self._modified: bool = False

        self._canvas = DrawingCanvas()
        self._canvas.shapes_changed.connect(self._on_shapes_changed)

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

        self._create_shared_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # Shared actions (created once, reused in menu and toolbar)
    # ------------------------------------------------------------------

    def _create_shared_actions(self):
        self._act_undo = QAction("&Undo", self)
        self._act_undo.setShortcut(QKeySequence.Undo)
        self._act_undo.triggered.connect(self._canvas.undo)

        self._act_clear = QAction("&Clear Canvas", self)
        self._act_clear.triggered.connect(self._action_clear)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def _build_menu(self):
        menu_bar = self.menuBar()

        # --- File menu ---
        file_menu = menu_bar.addMenu("&File")

        act_new = QAction("&New", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self._action_new)
        file_menu.addAction(act_new)

        act_open = QAction("&Open…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._action_open)
        file_menu.addAction(act_open)

        act_save = QAction("&Save", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._action_save)
        file_menu.addAction(act_save)

        act_save_as = QAction("Save &As…", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._action_save_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # --- Edit menu ---
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self._act_undo)
        edit_menu.addSeparator()
        edit_menu.addAction(self._act_clear)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = QToolBar("Tools", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Drawing tools
        self._tool_actions = {}
        tools = [
            (Tool.SELECT, "Select (S)"),
            (Tool.LINE, "Line (L)"),
            (Tool.RECTANGLE, "Rectangle (R)"),
            (Tool.CIRCLE, "Circle (C)"),
        ]
        for tool_id, label in tools:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setData(tool_id)
            act.triggered.connect(self._on_tool_selected)
            toolbar.addAction(act)
            self._tool_actions[tool_id] = act

        # Default tool
        self._tool_actions[Tool.LINE].setChecked(True)

        toolbar.addSeparator()

        # Pen width
        toolbar.addWidget(QLabel(" Width: "))
        self._spin_width = QSpinBox()
        self._spin_width.setRange(1, 20)
        self._spin_width.setValue(2)
        self._spin_width.valueChanged.connect(self._canvas.set_pen_width)
        toolbar.addWidget(self._spin_width)

        toolbar.addSeparator()

        # Color picker
        self._color_label = QLabel("  ")
        self._color_label.setStyleSheet("background-color: black; border: 1px solid gray;")
        self._color_label.setFixedSize(24, 24)
        toolbar.addWidget(self._color_label)

        act_color = QAction("Color…", self)
        act_color.triggered.connect(self._action_pick_color)
        toolbar.addAction(act_color)

        toolbar.addSeparator()
        toolbar.addAction(self._act_undo)
        toolbar.addAction(self._act_clear)

        # Keyboard shortcuts for tools
        self._setup_tool_shortcuts()

    def _setup_tool_shortcuts(self):
        shortcuts = {
            "S": Tool.SELECT,
            "L": Tool.LINE,
            "R": Tool.RECTANGLE,
            "C": Tool.CIRCLE,
        }
        for key, tool_id in shortcuts.items():
            act = QAction(self)
            act.setShortcut(QKeySequence(key))
            act.setData(tool_id)
            act.triggered.connect(self._on_tool_selected)
            self.addAction(act)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._label_file = QLabel("Untitled")
        self._label_shapes = QLabel("Shapes: 0")
        self._status_bar.addWidget(self._label_file, 1)
        self._status_bar.addPermanentWidget(self._label_shapes)

    def _update_status(self):
        file_name = os.path.basename(self._current_file) if self._current_file else "Untitled"
        if self._modified:
            file_name += " *"
        self._label_file.setText(file_name)
        self._label_shapes.setText(f"Shapes: {len(self._canvas.shapes)}")
        title = "Vector Drawing Board"
        if self._current_file:
            title += f" — {file_name}"
        self.setWindowTitle(title)

    # ------------------------------------------------------------------
    # Slots / actions
    # ------------------------------------------------------------------

    def _on_tool_selected(self):
        action = self.sender()
        if action is None:
            return
        tool_id = action.data()
        self._canvas.set_tool(tool_id)
        for tid, act in self._tool_actions.items():
            act.setChecked(tid == tool_id)

    def _on_shapes_changed(self):
        self._modified = True
        self._update_status()

    def _action_pick_color(self):
        color = QColorDialog.getColor(self._canvas.current_color, self, "Pick Color")
        if color.isValid():
            self._canvas.set_color(color)
            self._color_label.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid gray;"
            )

    def _action_new(self):
        if not self._confirm_discard():
            return
        self._canvas.clear()
        self._current_file = ""
        self._modified = False
        self._update_status()

    def _action_open(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Drawing", "", "Vector Drawing (*.vdb);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._canvas.shapes_from_dict(data)
            self._current_file = path
            self._modified = False
            self._update_status()
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            QMessageBox.critical(self, "Open Error", f"Failed to open file:\n{exc}")

    def _action_save(self):
        if not self._current_file:
            self._action_save_as()
        else:
            self._save_to(self._current_file)

    def _action_save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Drawing", "", "Vector Drawing (*.vdb);;All Files (*)"
        )
        if path:
            self._save_to(path)

    def _save_to(self, path: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._canvas.shapes_to_dict(), f, indent=2)
            self._current_file = path
            self._modified = False
            self._update_status()
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{exc}")

    def _action_clear(self):
        reply = QMessageBox.question(
            self, "Clear Canvas",
            "Are you sure you want to clear the canvas?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._canvas.clear()

    def _confirm_discard(self) -> bool:
        if not self._modified:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
