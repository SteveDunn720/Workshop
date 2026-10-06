from dataclasses import dataclass


@dataclass
class SurfaceBinding:
    """
    Describes where one target vertex exists on the source surface.

    The target position can be reconstructed from the three source
    triangle vertices using the stored barycentric weights.
    """

    target_index: int

    source_face: int
    source_triangle: int

    source_vertices: tuple[int, int, int]
    barycentric: tuple[float, float, float]


@dataclass
class TopologyMap:
    """
    Mapping from one polygon topology to another.

    The map itself is independent of specific Maya node names, allowing
    the same topology relationship to be reused between characters.
    """

    source_vertex_count: int
    target_vertex_count: int

    bindings: list[SurfaceBinding]