// A small, dependency-free force-directed layout (Fruchterman-Reingold
// style) for the Knowledge Graph view. Deliberately not a new charting
// dependency -- the graph is small enough (provenance-derived, not a
// firehose) that a plain iterative relaxation is both sufficient and
// avoids adding a graph-rendering library for one page.

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
}

/** Deterministic pseudo-random in [0, 1), seeded by index -- avoids a
 * different layout on every re-render for the same graph. */
function seeded(i: number): number {
  const x = Math.sin(i * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

export function computeForceLayout(
  nodeIds: string[],
  edges: { source: string; target: string }[],
  width: number,
  height: number,
  iterations = 200,
): Map<string, LayoutNode> {
  const positions = new Map<string, LayoutNode>();
  nodeIds.forEach((id, i) => {
    positions.set(id, {
      id,
      x: width / 2 + (seeded(i * 2) - 0.5) * width * 0.8,
      y: height / 2 + (seeded(i * 2 + 1) - 0.5) * height * 0.8,
    });
  });

  if (nodeIds.length === 0) return positions;

  const area = width * height;
  const k = Math.sqrt(area / nodeIds.length);
  const validEdges = edges.filter((e) => positions.has(e.source) && positions.has(e.target));

  let temperature = width / 10;
  const cooling = temperature / iterations;

  for (let iter = 0; iter < iterations; iter++) {
    const displacement = new Map<string, { dx: number; dy: number }>();
    for (const id of nodeIds) displacement.set(id, { dx: 0, dy: 0 });

    // Repulsion between every pair -- O(n^2), fine for graphs in the
    // hundreds of nodes this platform currently produces.
    for (let i = 0; i < nodeIds.length; i++) {
      const a = positions.get(nodeIds[i])!;
      for (let j = i + 1; j < nodeIds.length; j++) {
        const b = positions.get(nodeIds[j])!;
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const force = (k * k) / dist;
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        const da = displacement.get(a.id)!;
        da.dx += dx;
        da.dy += dy;
        const db = displacement.get(b.id)!;
        db.dx -= dx;
        db.dy -= dy;
      }
    }

    // Attraction along edges.
    for (const edge of validEdges) {
      const a = positions.get(edge.source)!;
      const b = positions.get(edge.target)!;
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const force = (dist * dist) / k;
      dx = (dx / dist) * force;
      dy = (dy / dist) * force;
      const da = displacement.get(a.id)!;
      da.dx -= dx;
      da.dy -= dy;
      const db = displacement.get(b.id)!;
      db.dx += dx;
      db.dy += dy;
    }

    // Apply, clamped by temperature, then cool.
    for (const id of nodeIds) {
      const pos = positions.get(id)!;
      const disp = displacement.get(id)!;
      const dist = Math.sqrt(disp.dx * disp.dx + disp.dy * disp.dy) || 0.01;
      const clamped = Math.min(dist, temperature);
      pos.x += (disp.dx / dist) * clamped;
      pos.y += (disp.dy / dist) * clamped;
      // Keep a margin so node circles and their labels never clip the
      // canvas edge.
      const margin = 60;
      pos.x = Math.min(width - margin, Math.max(margin, pos.x));
      pos.y = Math.min(height - margin, Math.max(margin, pos.y));
    }
    temperature -= cooling;
  }

  return positions;
}
