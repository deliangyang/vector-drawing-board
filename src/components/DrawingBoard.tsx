import { useRef, useEffect, useCallback } from 'react';
import { useDrawing } from '../hooks/useDrawing';
import { Toolbar } from './Toolbar';
import type { ToolType } from '../types/shapes';

const CANVAS_W = 1200;
const CANVAS_H = 800;

export function DrawingBoard() {
  const {
    canvasRef,
    selectedId,
    state,
    setState,
    undo,
    redo,
    clearAll,
    deleteSelected,
    exportPNG,
    canUndo,
    canRedo,
  } = useDrawing();

  const containerRef = useRef<HTMLDivElement>(null);

  // keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        undo();
      } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
        e.preventDefault();
        redo();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        deleteSelected();
      }
    },
    [undo, redo, deleteSelected],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const setCursorForTool = (tool: ToolType) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const cursorMap: Record<ToolType, string> = {
      select: 'default',
      pen: 'crosshair',
      line: 'crosshair',
      rect: 'crosshair',
      ellipse: 'crosshair',
      text: 'text',
      eraser: 'cell',
    };
    canvas.style.cursor = cursorMap[tool] ?? 'crosshair';
  };

  const handleToolChange = (t: ToolType) => {
    setState((s) => ({ ...s, tool: t }));
    setCursorForTool(t);
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1 className="app-title">🎨 Vector Drawing Board</h1>
        <span className="app-subtitle">Multi-terminal vector drawing application</span>
      </header>
      <div className="app-body">
        <Toolbar
          tool={state.tool}
          color={state.color}
          strokeWidth={state.strokeWidth}
          fill={state.fill}
          opacity={state.opacity}
          fontSize={state.fontSize}
          canUndo={canUndo}
          canRedo={canRedo}
          hasSelection={!!selectedId}
          onToolChange={handleToolChange}
          onColorChange={(c) => setState((s) => ({ ...s, color: c }))}
          onStrokeWidthChange={(w) => setState((s) => ({ ...s, strokeWidth: w }))}
          onFillChange={(f) => setState((s) => ({ ...s, fill: f }))}
          onOpacityChange={(o) => setState((s) => ({ ...s, opacity: o }))}
          onFontSizeChange={(fs) => setState((s) => ({ ...s, fontSize: fs }))}
          onUndo={undo}
          onRedo={redo}
          onClear={clearAll}
          onDelete={deleteSelected}
          onExport={exportPNG}
        />
        <main className="canvas-container" ref={containerRef}>
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            className="drawing-canvas"
            style={{ cursor: 'crosshair' }}
          />
        </main>
      </div>
    </div>
  );
}
