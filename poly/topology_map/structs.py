from dataclasses import dataclass


@dataclass
class TopologyFingerprint:
    """
    Identifies a specific polygon topology.

    Positions are intentionally not included, so differently shaped
    meshes with identical topology produce the same fingerprint.
    """

    vertex_count: int
    edge_count: int
    face_count: int
    connectivity_hash: str


@dataclass
class SurfaceBinding:
    """
    Describes where one target vertex exists on the source surface.
    """

    target_index: int

    source_face: int
    source_triangle: int

    source_vertices: tuple[int, int, int]
    barycentric: tuple[float, float, float]

    source_polygroup: int | None = None

@dataclass
class MeshTopology:
    """
    Complete polygon connectivity required to reconstruct a mesh.
    """

    vertex_count: int

    # One tuple per polygon containing its vertex IDs.
    faces: list[tuple[int, ...]]

@dataclass
class MeshSnapshot:
    """
    Complete reconstructable mesh data.
    """

    fingerprint: TopologyFingerprint
    topology: MeshTopology

    positions: list[
        tuple[float, float, float]
    ]

@dataclass
class TopologyMap:

    source_fingerprint: TopologyFingerprint
    target_fingerprint: TopologyFingerprint

    bindings: list[SurfaceBinding]

    source_snapshot: MeshSnapshot | None = None
    target_snapshot: MeshSnapshot | None = None


    


