import type { Shape, Point } from '../types/shapes';

export function generateId(): string {
  return Math.random().toString(36).slice(2, 11);
}

export function getCanvasPoint(canvas: HTMLCanvasElement, clientX: number, clientY: number): Point {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  };
}

export function drawShape(ctx: CanvasRenderingContext2D, shape: Shape): void {
  ctx.save();
  ctx.globalAlpha = shape.opacity;
  ctx.strokeStyle = shape.color;
  ctx.lineWidth = shape.strokeWidth;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.fillStyle = shape.fill;

  switch (shape.type) {
    case 'pen': {
      if (shape.points.length < 2) break;
      ctx.beginPath();
      ctx.moveTo(shape.points[0].x, shape.points[0].y);
      for (let i = 1; i < shape.points.length; i++) {
        ctx.lineTo(shape.points[i].x, shape.points[i].y);
      }
      ctx.stroke();
      break;
    }
    case 'line': {
      ctx.beginPath();
      ctx.moveTo(shape.x1, shape.y1);
      ctx.lineTo(shape.x2, shape.y2);
      ctx.stroke();
      break;
    }
    case 'rect': {
      ctx.beginPath();
      ctx.rect(shape.x, shape.y, shape.width, shape.height);
      if (shape.fill !== 'transparent') ctx.fill();
      ctx.stroke();
      break;
    }
    case 'ellipse': {
      ctx.beginPath();
      ctx.ellipse(shape.cx, shape.cy, Math.abs(shape.rx), Math.abs(shape.ry), 0, 0, Math.PI * 2);
      if (shape.fill !== 'transparent') ctx.fill();
      ctx.stroke();
      break;
    }
    case 'text': {
      ctx.font = `${shape.fontSize}px sans-serif`;
      ctx.fillStyle = shape.color;
      ctx.fillText(shape.text, shape.x, shape.y);
      break;
    }
  }

  ctx.restore();
}

export function renderAll(
  ctx: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  shapes: Shape[],
  selectedId: string | null,
): void {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  shapes.forEach((shape) => {
    drawShape(ctx, shape);
    if (shape.id === selectedId) {
      drawSelectionIndicator(ctx, shape);
    }
  });
}

function drawSelectionIndicator(ctx: CanvasRenderingContext2D, shape: Shape): void {
  ctx.save();
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 4]);

  const pad = 4;

  switch (shape.type) {
    case 'rect': {
      ctx.strokeRect(
        shape.x - pad,
        shape.y - pad,
        shape.width + pad * 2,
        shape.height + pad * 2,
      );
      break;
    }
    case 'ellipse': {
      ctx.beginPath();
      ctx.ellipse(
        shape.cx,
        shape.cy,
        Math.abs(shape.rx) + pad,
        Math.abs(shape.ry) + pad,
        0, 0, Math.PI * 2,
      );
      ctx.stroke();
      break;
    }
    case 'line': {
      ctx.strokeRect(
        Math.min(shape.x1, shape.x2) - pad,
        Math.min(shape.y1, shape.y2) - pad,
        Math.abs(shape.x2 - shape.x1) + pad * 2,
        Math.abs(shape.y2 - shape.y1) + pad * 2,
      );
      break;
    }
    case 'pen': {
      if (shape.points.length === 0) break;
      const xs = shape.points.map((p) => p.x);
      const ys = shape.points.map((p) => p.y);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);
      ctx.strokeRect(minX - pad, minY - pad, maxX - minX + pad * 2, maxY - minY + pad * 2);
      break;
    }
    case 'text': {
      ctx.font = `${shape.fontSize}px sans-serif`;
      const metrics = ctx.measureText(shape.text);
      ctx.strokeRect(
        shape.x - pad,
        shape.y - shape.fontSize - pad,
        metrics.width + pad * 2,
        shape.fontSize + pad * 2,
      );
      break;
    }
  }

  ctx.restore();
}

export function isPointInShape(shape: Shape, p: Point): boolean {
  const tolerance = 8;
  switch (shape.type) {
    case 'rect': {
      return (
        p.x >= shape.x - tolerance &&
        p.x <= shape.x + shape.width + tolerance &&
        p.y >= shape.y - tolerance &&
        p.y <= shape.y + shape.height + tolerance
      );
    }
    case 'ellipse': {
      const dx = (p.x - shape.cx) / (Math.abs(shape.rx) + tolerance);
      const dy = (p.y - shape.cy) / (Math.abs(shape.ry) + tolerance);
      return dx * dx + dy * dy <= 1;
    }
    case 'line': {
      const A = p.x - shape.x1;
      const B = p.y - shape.y1;
      const C = shape.x2 - shape.x1;
      const D = shape.y2 - shape.y1;
      const dot = A * C + B * D;
      const lenSq = C * C + D * D;
      let t = lenSq !== 0 ? dot / lenSq : -1;
      t = Math.max(0, Math.min(1, t));
      const nearX = shape.x1 + t * C;
      const nearY = shape.y1 + t * D;
      return Math.hypot(p.x - nearX, p.y - nearY) <= tolerance;
    }
    case 'pen': {
      for (let i = 1; i < shape.points.length; i++) {
        const a = shape.points[i - 1];
        const b = shape.points[i];
        const A = p.x - a.x;
        const B = p.y - a.y;
        const C = b.x - a.x;
        const D = b.y - a.y;
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let t = lenSq !== 0 ? dot / lenSq : 0;
        t = Math.max(0, Math.min(1, t));
        const nearX = a.x + t * C;
        const nearY = a.y + t * D;
        if (Math.hypot(p.x - nearX, p.y - nearY) <= tolerance) return true;
      }
      return false;
    }
    case 'text': {
      return (
        p.x >= shape.x - tolerance &&
        p.x <= shape.x + 200 &&
        p.y >= shape.y - shape.fontSize - tolerance &&
        p.y <= shape.y + tolerance
      );
    }
    default:
      return false;
  }
}
