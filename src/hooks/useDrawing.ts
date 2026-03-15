import { useRef, useState, useCallback, useEffect, useLayoutEffect } from 'react';
import type { Shape, ToolType, Point, PenShape } from '../types/shapes';
import { generateId, getCanvasPoint, renderAll, isPointInShape } from '../utils/canvas';

export interface DrawingState {
  color: string;
  strokeWidth: number;
  fill: string;
  opacity: number;
  tool: ToolType;
  fontSize: number;
}

interface UseDrawingReturn {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  shapes: Shape[];
  selectedId: string | null;
  state: DrawingState;
  setState: React.Dispatch<React.SetStateAction<DrawingState>>;
  undo: () => void;
  redo: () => void;
  clearAll: () => void;
  deleteSelected: () => void;
  exportPNG: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export function useDrawing(): UseDrawingReturn {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [state, setState] = useState<DrawingState>({
    color: '#1a1a1a',
    strokeWidth: 3,
    fill: 'transparent',
    opacity: 1,
    tool: 'pen',
    fontSize: 20,
  });

  // undo/redo state (use real state so canUndo/canRedo are reactive)
  const [historyIndex, setHistoryIndex] = useState(0);
  const [historyLength, setHistoryLength] = useState(1);

  // mutable refs for use inside event handlers (avoid stale closures)
  const historyRef = useRef<Shape[][]>([[]]);
  const historyIndexRef = useRef(0);
  const isDrawingRef = useRef(false);
  const currentShapeRef = useRef<Shape | null>(null);
  const dragStartRef = useRef<Point | null>(null);
  const dragShapeOrigRef = useRef<Shape | null>(null);

  // sync mutable refs from React state (after render, so handlers see latest)
  const stateRef = useRef(state);
  const shapesRef = useRef(shapes);
  const selectedIdRef = useRef(selectedId);

  useLayoutEffect(() => {
    stateRef.current = state;
  });
  useLayoutEffect(() => {
    shapesRef.current = shapes;
  });
  useLayoutEffect(() => {
    selectedIdRef.current = selectedId;
  });

  // re-render canvas whenever shapes/selectedId change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    renderAll(ctx, canvas, shapes, selectedId);
  }, [shapes, selectedId]);

  const pushHistory = useCallback((newShapes: Shape[]) => {
    const idx = historyIndexRef.current;
    historyRef.current = historyRef.current.slice(0, idx + 1);
    historyRef.current.push(newShapes);
    const newIdx = historyRef.current.length - 1;
    historyIndexRef.current = newIdx;
    setShapes(newShapes);
    setHistoryIndex(newIdx);
    setHistoryLength(historyRef.current.length);
  }, []);

  const getPoint = useCallback((e: MouseEvent | TouchEvent): Point | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    if ('touches' in e) {
      if (e.touches.length === 0) return null;
      return getCanvasPoint(canvas, e.touches[0].clientX, e.touches[0].clientY);
    }
    return getCanvasPoint(canvas, (e as MouseEvent).clientX, (e as MouseEvent).clientY);
  }, []);

  const handlePointerDown = useCallback((e: MouseEvent | TouchEvent) => {
    e.preventDefault();
    const p = getPoint(e);
    if (!p) return;
    const { tool, color, strokeWidth, fill, opacity, fontSize } = stateRef.current;
    const currentShapes = shapesRef.current;

    if (tool === 'select') {
      let found: Shape | null = null;
      for (let i = currentShapes.length - 1; i >= 0; i--) {
        if (isPointInShape(currentShapes[i], p)) {
          found = currentShapes[i];
          break;
        }
      }
      setSelectedId(found ? found.id : null);
      if (found) {
        dragStartRef.current = p;
        dragShapeOrigRef.current = found;
        isDrawingRef.current = true;
      }
      return;
    }

    if (tool === 'eraser') {
      for (let i = currentShapes.length - 1; i >= 0; i--) {
        if (isPointInShape(currentShapes[i], p)) {
          const id = currentShapes[i].id;
          pushHistory(currentShapes.filter((s) => s.id !== id));
          if (selectedIdRef.current === id) setSelectedId(null);
          break;
        }
      }
      return;
    }

    if (tool === 'text') {
      const text = prompt('Enter text:');
      if (text) {
        pushHistory([
          ...currentShapes,
          {
            id: generateId(),
            type: 'text',
            x: p.x,
            y: p.y,
            text,
            color,
            strokeWidth,
            fill,
            opacity,
            fontSize,
          },
        ]);
      }
      return;
    }

    isDrawingRef.current = true;
    const id = generateId();

    if (tool === 'pen') {
      currentShapeRef.current = { id, type: 'pen', points: [p], color, strokeWidth, fill, opacity };
    } else if (tool === 'line') {
      currentShapeRef.current = { id, type: 'line', x1: p.x, y1: p.y, x2: p.x, y2: p.y, color, strokeWidth, fill, opacity };
    } else if (tool === 'rect') {
      currentShapeRef.current = { id, type: 'rect', x: p.x, y: p.y, width: 0, height: 0, color, strokeWidth, fill, opacity };
    } else if (tool === 'ellipse') {
      currentShapeRef.current = { id, type: 'ellipse', cx: p.x, cy: p.y, rx: 0, ry: 0, color, strokeWidth, fill, opacity };
    }
  }, [getPoint, pushHistory]);

  const handlePointerMove = useCallback((e: MouseEvent | TouchEvent) => {
    e.preventDefault();
    if (!isDrawingRef.current) return;
    const p = getPoint(e);
    if (!p) return;
    const { tool } = stateRef.current;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (tool === 'select' && dragStartRef.current && dragShapeOrigRef.current) {
      const dx = p.x - dragStartRef.current.x;
      const dy = p.y - dragStartRef.current.y;
      const orig = dragShapeOrigRef.current;
      let moved: Shape;
      switch (orig.type) {
        case 'rect':
          moved = { ...orig, x: orig.x + dx, y: orig.y + dy }; break;
        case 'ellipse':
          moved = { ...orig, cx: orig.cx + dx, cy: orig.cy + dy }; break;
        case 'line':
          moved = { ...orig, x1: orig.x1 + dx, y1: orig.y1 + dy, x2: orig.x2 + dx, y2: orig.y2 + dy }; break;
        case 'pen':
          moved = { ...orig, points: orig.points.map((pt) => ({ x: pt.x + dx, y: pt.y + dy })) }; break;
        case 'text':
          moved = { ...orig, x: orig.x + dx, y: orig.y + dy }; break;
        default:
          return;
      }
      const newShapes = shapesRef.current.map((s) => (s.id === moved.id ? moved : s));
      setShapes(newShapes);
      renderAll(ctx, canvas, newShapes, moved.id);
      return;
    }

    const shape = currentShapeRef.current;
    if (!shape) return;

    if (shape.type === 'pen') {
      (shape as PenShape).points.push(p);
    } else if (shape.type === 'line') {
      shape.x2 = p.x; shape.y2 = p.y;
    } else if (shape.type === 'rect') {
      shape.width = p.x - shape.x; shape.height = p.y - shape.y;
    } else if (shape.type === 'ellipse') {
      shape.rx = p.x - shape.cx; shape.ry = p.y - shape.cy;
    }

    renderAll(ctx, canvas, [...shapesRef.current, shape], null);
  }, [getPoint]);

  const handlePointerUp = useCallback((e: MouseEvent | TouchEvent) => {
    e.preventDefault();
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    const { tool } = stateRef.current;

    if (tool === 'select' && dragShapeOrigRef.current) {
      pushHistory(shapesRef.current);
      dragStartRef.current = null;
      dragShapeOrigRef.current = null;
      return;
    }

    const shape = currentShapeRef.current;
    if (!shape) return;

    let skip = false;
    if (shape.type === 'pen' && shape.points.length < 2) skip = true;
    if (shape.type === 'line' && shape.x1 === shape.x2 && shape.y1 === shape.y2) skip = true;
    if (shape.type === 'rect' && shape.width === 0 && shape.height === 0) skip = true;
    if (shape.type === 'ellipse' && shape.rx === 0 && shape.ry === 0) skip = true;

    if (!skip) {
      pushHistory([...shapesRef.current, shape]);
    }
    currentShapeRef.current = null;
  }, [pushHistory]);

  // Attach canvas events
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const opts = { passive: false };
    canvas.addEventListener('mousedown', handlePointerDown, opts);
    canvas.addEventListener('mousemove', handlePointerMove, opts);
    canvas.addEventListener('mouseup', handlePointerUp, opts);
    canvas.addEventListener('mouseleave', handlePointerUp, opts);
    canvas.addEventListener('touchstart', handlePointerDown, opts);
    canvas.addEventListener('touchmove', handlePointerMove, opts);
    canvas.addEventListener('touchend', handlePointerUp, opts);
    return () => {
      canvas.removeEventListener('mousedown', handlePointerDown);
      canvas.removeEventListener('mousemove', handlePointerMove);
      canvas.removeEventListener('mouseup', handlePointerUp);
      canvas.removeEventListener('mouseleave', handlePointerUp);
      canvas.removeEventListener('touchstart', handlePointerDown);
      canvas.removeEventListener('touchmove', handlePointerMove);
      canvas.removeEventListener('touchend', handlePointerUp);
    };
  }, [handlePointerDown, handlePointerMove, handlePointerUp]);

  const undo = useCallback(() => {
    const idx = historyIndexRef.current;
    if (idx <= 0) return;
    const newIdx = idx - 1;
    historyIndexRef.current = newIdx;
    const prev = historyRef.current[newIdx];
    setShapes(prev);
    setSelectedId(null);
    setHistoryIndex(newIdx);
  }, []);

  const redo = useCallback(() => {
    const idx = historyIndexRef.current;
    if (idx >= historyRef.current.length - 1) return;
    const newIdx = idx + 1;
    historyIndexRef.current = newIdx;
    const next = historyRef.current[newIdx];
    setShapes(next);
    setSelectedId(null);
    setHistoryIndex(newIdx);
  }, []);

  const clearAll = useCallback(() => {
    pushHistory([]);
    setSelectedId(null);
  }, [pushHistory]);

  const deleteSelected = useCallback(() => {
    const id = selectedIdRef.current;
    if (!id) return;
    pushHistory(shapesRef.current.filter((s) => s.id !== id));
    setSelectedId(null);
  }, [pushHistory]);

  const exportPNG = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = 'drawing.png';
    a.click();
  }, []);

  return {
    canvasRef,
    shapes,
    selectedId,
    state,
    setState,
    undo,
    redo,
    clearAll,
    deleteSelected,
    exportPNG,
    canUndo: historyIndex > 0,
    canRedo: historyIndex < historyLength - 1,
  };
}
