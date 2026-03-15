# vector-drawing-board

A multi-terminal vector drawing board built with React + TypeScript + Vite. Works on desktop browsers and mobile/touch devices.

## Features

- ✏️ **Freehand pen** drawing
- ╱ **Line** tool
- ▭ **Rectangle** tool
- ⬭ **Ellipse** tool
- **T Text** tool
- ↖ **Select & Move** shapes
- ⌫ **Eraser** to remove shapes
- 🎨 **Stroke color** and **fill color** pickers
- Adjustable **stroke width** and **opacity**
- **Undo / Redo** (keyboard: `Ctrl+Z` / `Ctrl+Y`)
- **Delete** selected shape (`Delete` key)
- **Export** canvas as PNG
- Responsive UI for desktop and mobile

## Getting Started

```bash
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

## Build

```bash
npm run build
```

The production output is placed in the `dist/` directory.

## Tech Stack

- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite 8](https://vitejs.dev/) for bundling
- HTML5 Canvas API for rendering
