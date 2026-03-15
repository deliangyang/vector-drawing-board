import React from 'react';
import type { ToolType } from '../types/shapes';

interface ToolButtonProps {
  active: boolean;
  onClick: () => void;
  title: string;
  children: React.ReactNode;
}

function ToolButton({ active, onClick, title, children }: ToolButtonProps) {
  return (
    <button
      title={title}
      onClick={onClick}
      className={`tool-btn${active ? ' active' : ''}`}
    >
      {children}
    </button>
  );
}

interface ToolbarProps {
  tool: ToolType;
  color: string;
  strokeWidth: number;
  fill: string;
  opacity: number;
  fontSize: number;
  canUndo: boolean;
  canRedo: boolean;
  hasSelection: boolean;
  onToolChange: (t: ToolType) => void;
  onColorChange: (c: string) => void;
  onStrokeWidthChange: (w: number) => void;
  onFillChange: (f: string) => void;
  onOpacityChange: (o: number) => void;
  onFontSizeChange: (s: number) => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
  onDelete: () => void;
  onExport: () => void;
}

const TOOLS: { type: ToolType; title: string; icon: string }[] = [
  { type: 'select', title: 'Select / Move', icon: '↖' },
  { type: 'pen', title: 'Pen (freehand)', icon: '✏️' },
  { type: 'line', title: 'Line', icon: '╱' },
  { type: 'rect', title: 'Rectangle', icon: '▭' },
  { type: 'ellipse', title: 'Ellipse', icon: '⬭' },
  { type: 'text', title: 'Text', icon: 'T' },
  { type: 'eraser', title: 'Eraser', icon: '⌫' },
];

export function Toolbar({
  tool,
  color,
  strokeWidth,
  fill,
  opacity,
  fontSize,
  canUndo,
  canRedo,
  hasSelection,
  onToolChange,
  onColorChange,
  onStrokeWidthChange,
  onFillChange,
  onOpacityChange,
  onFontSizeChange,
  onUndo,
  onRedo,
  onClear,
  onDelete,
  onExport,
}: ToolbarProps) {
  return (
    <aside className="toolbar">
      <div className="toolbar-section">
        <span className="toolbar-label">Tools</span>
        <div className="tool-grid">
          {TOOLS.map(({ type, title, icon }) => (
            <ToolButton
              key={type}
              active={tool === type}
              onClick={() => onToolChange(type)}
              title={title}
            >
              {icon}
            </ToolButton>
          ))}
        </div>
      </div>

      <div className="toolbar-section">
        <span className="toolbar-label">Stroke Color</span>
        <input
          type="color"
          value={color}
          onChange={(e) => onColorChange(e.target.value)}
          title="Stroke color"
          className="color-input"
        />
      </div>

      <div className="toolbar-section">
        <span className="toolbar-label">Fill Color</span>
        <div className="fill-row">
          <input
            type="color"
            value={fill === 'transparent' ? '#ffffff' : fill}
            onChange={(e) => onFillChange(e.target.value)}
            title="Fill color"
            className="color-input"
          />
          <button
            className={`fill-toggle${fill === 'transparent' ? ' active' : ''}`}
            onClick={() => onFillChange(fill === 'transparent' ? '#ffffff' : 'transparent')}
            title="Toggle transparent fill"
          >
            None
          </button>
        </div>
      </div>

      <div className="toolbar-section">
        <span className="toolbar-label">Stroke Width: {strokeWidth}px</span>
        <input
          type="range"
          min={1}
          max={30}
          value={strokeWidth}
          onChange={(e) => onStrokeWidthChange(Number(e.target.value))}
          className="slider"
        />
      </div>

      <div className="toolbar-section">
        <span className="toolbar-label">Opacity: {Math.round(opacity * 100)}%</span>
        <input
          type="range"
          min={0}
          max={100}
          value={Math.round(opacity * 100)}
          onChange={(e) => onOpacityChange(Number(e.target.value) / 100)}
          className="slider"
        />
      </div>

      {tool === 'text' && (
        <div className="toolbar-section">
          <span className="toolbar-label">Font Size: {fontSize}px</span>
          <input
            type="range"
            min={10}
            max={80}
            value={fontSize}
            onChange={(e) => onFontSizeChange(Number(e.target.value))}
            className="slider"
          />
        </div>
      )}

      <div className="toolbar-section toolbar-actions">
        <button onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)" className="action-btn">
          ↩ Undo
        </button>
        <button onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl+Y)" className="action-btn">
          ↪ Redo
        </button>
        <button
          onClick={onDelete}
          disabled={!hasSelection}
          title="Delete selected"
          className="action-btn danger"
        >
          🗑 Delete
        </button>
        <button onClick={onClear} title="Clear canvas" className="action-btn danger">
          ✕ Clear
        </button>
        <button onClick={onExport} title="Export as PNG" className="action-btn export">
          ⬇ Export PNG
        </button>
      </div>
    </aside>
  );
}
