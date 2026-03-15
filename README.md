# Vector Drawing Board

A cross-platform Python desktop application for creating and managing vector drawings, built with PyQt5.

## Features

- **Drawing tools**: Line, Rectangle, and Circle
- **Select tool**: Click to select shapes
- **Colour picker**: Choose any stroke colour
- **Pen width**: Adjustable 1–20 px
- **Undo**: Remove the last-added shape (Ctrl+Z)
- **Clear canvas**: Wipe all shapes at once
- **File management**: Save and open drawings in `.vdb` (JSON) format
- **Keyboard shortcuts**: `L` Line, `R` Rectangle, `C` Circle, `S` Select

## Project Structure

```
vector-drawing-board/
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── ui/
│   ├── __init__.py
│   └── main_window.py        # Main window, toolbar, menus
└── core/
    ├── __init__.py
    ├── drawing_canvas.py     # Interactive canvas widget
    └── shapes.py             # Shape classes (Line, Rectangle, Circle)
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
