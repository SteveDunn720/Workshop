"""Generate a wandering helix on an uncapped polygon tube in Maya.

Requires a tube with two boundary loops and consistent quad topology between them.
"""
from __future__ import annotations

import math
import random

import maya.api.OpenMaya as om

from Workshop.poly.meshes import get_mesh_shape, get_selected_mesh
from Workshop.nurbs.curve import create_curve_through_positions


def _smooth(values: list[float], passes: int = 5) -> list[float]:
    for _ in range(passes):
        values = [0.25 * values[max(0, i - 1)] + 0.5 * v +
                  0.25 * values[min(len(values) - 1, i + 1)]
                  for i, v in enumerate(values)]
    return values


def _mesh_rings(mesh: str) -> tuple[list[list[int]], om.MFnMesh]:
    selection = om.MSelectionList()
    selection.add(get_mesh_shape(mesh))
    dag = selection.getDagPath(0)
    if dag.node().hasFn(om.MFn.kTransform):
        dag.extendToShape()
    fn = om.MFnMesh(dag)
    if fn.numPolygons == 0:
        raise ValueError('Input must be a polygon mesh.')

    edges = om.MItMeshEdge(dag)
    boundary_edges = []
    adjacency = {}
    while not edges.isDone():
        if edges.onBoundary():
            a, b = edges.vertexId(0), edges.vertexId(1)
            boundary_edges.append((a, b))
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
        edges.next()
    if not boundary_edges or any(len(v) != 2 for v in adjacency.values()):
        raise ValueError('Expected exactly two clean boundary loops.')

    loops = []
    remaining = set(adjacency)
    while remaining:
        start = min(remaining)
        loop = [start]
        prev, current = -1, start
        while True:
            neighbors = adjacency[current]
            nxt = neighbors[0] if neighbors[0] != prev else neighbors[1]
            if nxt == start:
                break
            if nxt in loop:
                raise ValueError('Invalid boundary topology.')
            loop.append(nxt)
            prev, current = current, nxt
        remaining.difference_update(loop)
        loops.append(loop)
    if len(loops) != 2 or len(loops[0]) != len(loops[1]):
        raise ValueError('Expected two boundary loops with equal vertex counts.')

    # Follow the quad mesh from one end to the other. Every interior ring
    # must contain the same number of vertices as the boundary.
    vertex_neighbors = {i: set() for i in range(fn.numVertices)}
    for a, b in (fn.getEdgeVertices(i) for i in range(fn.numEdges)):
        vertex_neighbors[a].add(b)
        vertex_neighbors[b].add(a)
    rings = [loops[0]]
    visited = set(rings[0])
    end_set = set(loops[1])
    while set(rings[-1]) != end_set:
        current = rings[-1]
        next_ring = []
        for v in current:
            candidates = vertex_neighbors[v] - visited
            if len(candidates) != 1:
                raise ValueError('Requires a regular quad tube with longitudinal edges.')
            next_ring.append(next(iter(candidates)))
        if len(set(next_ring)) != len(current):
            raise ValueError('Tube rings do not map one-to-one.')
        visited.update(next_ring)
        rings.append(next_ring)
        if len(rings) > fn.numVertices:
            raise ValueError('Could not traverse the tube.')
    return rings, fn



def _noise(rng: random.Random, samples: int, scale: int) -> list[float]:
    """Smooth interpolated random values with controllable feature size."""
    anchors = [rng.uniform(-1.0, 1.0) for _ in range(max(3, scale + 1))]
    result = []
    for i in range(samples):
        x = i / (samples - 1) * (len(anchors) - 1)
        j = min(int(x), len(anchors) - 2)
        t = x - j
        t = t * t * (3 - 2 * t)
        result.append(anchors[j] * (1 - t) + anchors[j + 1] * t)
    return _smooth(result, 2)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def generate_surface_helix(
    mesh: str | None = None,
    turns: float = 4.0,
    samples: int = 150,
    randomness: float = 0.25,
    backtrack: float = 0.4,
    surface_offset: float = 0.05,
    seed: int | None = None,
    start_angle: float = 0.0,
    name: str = 'surface_helix_crv',
    mode: str = 'wandering',
) -> str:
    """Create a winding curve on an open, regularly quad-ringed polygon tube.

    Modes:
        progressive: monotonic length travel, reaching the far end.
        wandering: reversible length travel, reaching the far end.
        free: unconstrained length travel, no endpoint requirement.

    randomness/backtrack range from 0 to 1. start_angle is in radians.
    A smooth interpolating curve may deviate slightly from the sampled mesh.
    """
    if mode not in {'progressive', 'wandering', 'free'}:
        raise ValueError('mode must be progressive, wandering, or free')
    if samples < 4 or turns <= 0:
        raise ValueError('samples must be >= 4 and turns must be positive')
    if not 0 <= randomness <= 1 or not 0 <= backtrack <= 1:
        raise ValueError('randomness and backtrack must be between 0 and 1')
    if mesh is None:
        mesh = get_selected_mesh()
    if not mesh:
        raise ValueError('Provide a mesh or select a polygon mesh')

    rings, fn = _mesh_rings(mesh)
    positions = [[fn.getPoint(v, om.MSpace.kWorld) for v in ring] for ring in rings]
    count = len(positions[0])
    rng = random.Random(seed)
    angular = _noise(rng, samples, max(3, round(turns * 3)))
    longitudinal = _noise(rng, samples, max(3, round(turns * 2)))

    # Progressive: positive increments, normalized to exactly reach t=1.
    increments = [max(0.01, 1.0 + randomness * 0.95 * value)
                  for value in longitudinal[1:]]
    cumulative = [0.0]
    for step in increments:
        cumulative.append(cumulative[-1] + step)
    progressive = [v / cumulative[-1] for v in cumulative]

    points = []
    for i in range(samples):
        u = i / (samples - 1)
        envelope = math.sin(math.pi * u)
        if mode == 'progressive':
            t = progressive[i]
        elif mode == 'wandering':
            t = _clamp(u + backtrack * randomness * 0.75 * envelope * longitudinal[i])
        else:
            # A drift plus local fluctuations; deliberately not end-constrained.
            t = _clamp(0.5 + (u - 0.5) * (1.0 - backtrack) +
                       randomness * (0.15 + 0.6 * backtrack) * longitudinal[i])

        angle = start_angle + 2 * math.pi * (
            turns * u + randomness * 0.35 * envelope * angular[i]
        )
        ring_pos = t * (len(positions) - 1)
        r0 = min(int(ring_pos), len(positions) - 2)
        rt = ring_pos - r0
        side_pos = (angle / (2 * math.pi) * count) % count
        s0 = int(side_pos)
        st = side_pos - s0
        s1 = (s0 + 1) % count

        def sample_ring(index: int) -> om.MPoint:
            return positions[index][s0] + (
                positions[index][s1] - positions[index][s0]
            ) * st

        point = sample_ring(r0) + (
            sample_ring(r0 + 1) - sample_ring(r0)
        ) * rt
        center0 = sum((om.MVector(p) for p in positions[r0]), om.MVector()) / count
        center1 = sum((om.MVector(p) for p in positions[r0 + 1]), om.MVector()) / count
        center = center0 * (1 - rt) + center1 * rt
        outward = om.MVector(point) - center
        if outward.length() > 1e-8:
            point += outward.normal() * surface_offset
        points.append((point.x, point.y, point.z))

    return create_curve_through_positions(name=name, positions=points, degree=3)
