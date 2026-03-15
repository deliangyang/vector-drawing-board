export type ToolType = 'select' | 'pen' | 'line' | 'rect' | 'ellipse' | 'text' | 'eraser';

export interface Point {
  x: number;
  y: number;
}

interface BaseShape {
  id: string;
  color: string;
  strokeWidth: number;
  fill: string;
  opacity: number;
}

export interface PenShape extends BaseShape {
  type: 'pen';
  points: Point[];
}

export interface LineShape extends BaseShape {
  type: 'line';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface RectShape extends BaseShape {
  type: 'rect';
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface EllipseShape extends BaseShape {
  type: 'ellipse';
  cx: number;
  cy: number;
  rx: number;
  ry: number;
}

export interface TextShape extends BaseShape {
  type: 'text';
  x: number;
  y: number;
  text: string;
  fontSize: number;
}

export type Shape = PenShape | LineShape | RectShape | EllipseShape | TextShape;
