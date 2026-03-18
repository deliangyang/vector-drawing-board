# Terminal Board

A cross-platform Python desktop application for managing multiple terminal instances on an infinite canvas, built with PyQt5.

## Features

- **Infinite Canvas**: Place terminals anywhere on an unlimited workspace
- **Multiple Terminals**: Create and manage multiple terminal instances
- **Photoshop-style Navigation**: Pan canvas with Space+Drag or H key (hand tool)
- **Zoom Control**: Zoom in/out with Ctrl+Scroll or keyboard shortcuts
- **Real Terminal Emulation**: Full PTY support with ANSI color and interactive programs
- **Persistent Layout**: Automatically saves and restores terminal positions and zoom level
- **Draggable Terminals**: Move and resize terminal windows on the canvas

## Canvas Navigation (Photoshop-style)

- **Space + Drag**: Pan the canvas (temporary hand tool)
- **H Key**: Toggle hand tool mode for continuous panning
- **Middle Mouse + Drag**: Pan the canvas
- **Ctrl + Scroll**: Zoom in/out
- **Ctrl + +/-**: Zoom in/out
- **Ctrl + 0**: Reset zoom to 100%

## Terminal Operations

- **Ctrl + Shift + T**: Add a new terminal
- **Ctrl + Shift + L**: Auto-layout all terminals
- **Drag Terminal**: Move terminal cards on canvas
- **Resize Terminal**: Drag terminal edges to resize

## Project Structure

```
vector-drawing-board/
├── main.py                        # Application entry point
├── requirements.txt               # Python dependencies (PyQt5, pyte)
├── ui/
│   ├── __init__.py
│   ├── main_window.py             # Main window, menus, toolbars
│   ├── canvas_container.py        # Container for canvas and terminals
│   ├── draggable_scroll_area.py   # Scroll area with pan support
│   ├── terminal_card.py           # Draggable/resizable terminal card
│   └── terminal_widget.py         # PTY-based terminal emulator (pyte)
└── core/
    ├── __init__.py
    ├── drawing_canvas.py          # Canvas background with zoom
    └── shapes.py                  # (Legacy shape classes)
```

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Requirements

- Python 3.8+
- PyQt5 5.15+
- pyte 0.8+ (terminal emulation)

## Tips

- The canvas automatically expands as you add terminals
- Terminal positions and zoom level are saved automatically
- Use Space+Drag for quick canvas panning (like in Photoshop)
- Press H to switch to hand tool mode for continuous panning
