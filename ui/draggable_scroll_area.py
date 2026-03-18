"""Draggable scroll area for canvas panning."""

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent, QCursor
from PyQt5.QtWidgets import QScrollArea


class DraggableScrollArea(QScrollArea):
    """Scroll area that supports panning with middle mouse button or Space+Left mouse."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_panning = False
        self._pan_start_pos = QPoint()
        self._is_space_pressed = False
        self._is_hand_tool_active = False  # H 键切换手形工具模式
        
        # Enable mouse tracking to update cursor
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        
        # Ensure we can receive keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

    def mousePressEvent(self, event: QMouseEvent):
        # Middle mouse button, Space+Left mouse, or H tool+Left mouse starts panning
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and (self._is_space_pressed or self._is_hand_tool_active)
        ):
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            # Calculate delta movement
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            
            # Update scroll bar positions
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())
            
            event.accept()
        else:
            # Update cursor when space or hand tool is active
            if self._is_space_pressed or self._is_hand_tool_active:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            if self._is_panning:
                self._is_panning = False
                # Restore cursor based on space key or hand tool state
                if self._is_space_pressed or self._is_hand_tool_active:
                    self.setCursor(Qt.OpenHandCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._is_space_pressed = True
            if not self._is_panning:
                self.setCursor(Qt.OpenHandCursor)
            event.accept()
        elif event.key() == Qt.Key_H and not event.isAutoRepeat():
            # PS 风格：H 键切换手形工具
            self._is_hand_tool_active = not self._is_hand_tool_active
            if not self._is_panning:
                if self._is_hand_tool_active:
                    self.setCursor(Qt.OpenHandCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._is_space_pressed = False
            if not self._is_panning:
                self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def enterEvent(self, event):
        """确保鼠标进入时获得焦点，以便接收键盘事件。"""
        self.setFocus()
        super().enterEvent(event)
    
    def focusOutEvent(self, event):
        """Reset panning state when focus is lost."""
        self._is_space_pressed = False
        self._is_panning = False
        # Keep hand tool state even when focus is lost
        if not self._is_hand_tool_active:
            self.setCursor(Qt.ArrowCursor)
        super().focusOutEvent(event)
