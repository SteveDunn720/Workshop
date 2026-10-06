import json

from .structs import (
    MeshSnapshot,
    MeshTopology,
    SurfaceBinding,
    TopologyFingerprint,
    TopologyMap,
)


FORMAT_NAME = "WorkshopTopologyMap"
FORMAT_VERSION = 1


# ---------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------

def _fingerprint_to_dict(
    fingerprint: TopologyFingerprint,
) -> dict:
    """
    Convert a TopologyFingerprint to JSON-compatible data.
    """

    return {
        "vertex_count": fingerprint.vertex_count,
        "edge_count": fingerprint.edge_count,
        "face_count": fingerprint.face_count,
        "connectivity_hash": fingerprint.connectivity_hash,
    }


def _fingerprint_from_dict(
    data: dict,
) -> TopologyFingerprint:
    """
    Build a TopologyFingerprint from serialized data.
    """

    return TopologyFingerprint(
        vertex_count=data["vertex_count"],
        edge_count=data["edge_count"],
        face_count=data["face_count"],
        connectivity_hash=data["connectivity_hash"],
    )


# ---------------------------------------------------------
# Snapshots
# ---------------------------------------------------------

def _snapshot_to_dict(
    snapshot: MeshSnapshot,
) -> dict:
    """
    Convert a MeshSnapshot to JSON-compatible data.
    """

    return {
        "fingerprint": _fingerprint_to_dict(
            snapshot.fingerprint
        ),

        "topology": {
            "vertex_count":
                snapshot.topology.vertex_count,

            "faces": [
                list(face)
                for face in snapshot.topology.faces
            ],
        },

        "positions": [
            list(position)
            for position in snapshot.positions
        ],
    }


def _snapshot_from_dict(
    data: dict,
) -> MeshSnapshot:
    """
    Build a MeshSnapshot from serialized data.
    """

    topology_data = data["topology"]

    return MeshSnapshot(
        fingerprint=_fingerprint_from_dict(
            data["fingerprint"]
        ),

        topology=MeshTopology(
            vertex_count=topology_data[
                "vertex_count"
            ],

            faces=[
                tuple(face)
                for face in topology_data["faces"]
            ],
        ),

        positions=[
            tuple(position)
            for position in data["positions"]
        ],
    )


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

def save_topology_map(
    topology_map: TopologyMap,
    path: str,
):
    """
    Serialize a TopologyMap to JSON.
    """

    data = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,

        "source_fingerprint": _fingerprint_to_dict(
            topology_map.source_fingerprint
        ),

        "target_fingerprint": _fingerprint_to_dict(
            topology_map.target_fingerprint
        ),

        "bindings": [
            {
                "target_index":
                    binding.target_index,

                "source_face":
                    binding.source_face,

                "source_triangle":
                    binding.source_triangle,

                "source_vertices": list(
                    binding.source_vertices
                ),

                "barycentric": list(
                    binding.barycentric
                ),
            }
            for binding in topology_map.bindings
        ],
    }

    # ---------------------------------------------------------
    # Optional snapshots
    # ---------------------------------------------------------

    if topology_map.source_snapshot is not None:

        data["source_snapshot"] = _snapshot_to_dict(
            topology_map.source_snapshot
        )

    if topology_map.target_snapshot is not None:

        data["target_snapshot"] = _snapshot_to_dict(
            topology_map.target_snapshot
        )

    # ---------------------------------------------------------
    # Write AFTER all data has been added
    # ---------------------------------------------------------

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
        )


# ---------------------------------------------------------
# Load
# ---------------------------------------------------------

def load_topology_map(
    path: str,
) -> TopologyMap:
    """
    Load a TopologyMap from JSON.
    """

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    # ---------------------------------------------------------
    # Validate format
    # ---------------------------------------------------------

    if data.get("format") != FORMAT_NAME:

        raise ValueError(
            f"{path} is not a Workshop TopologyMap."
        )

    version = data.get("version")

    if version != FORMAT_VERSION:

        raise ValueError(
            f"Unsupported TopologyMap version: {version}. "
            f"Expected version {FORMAT_VERSION}."
        )

    # ---------------------------------------------------------
    # Bindings
    # ---------------------------------------------------------

    bindings = [
        SurfaceBinding(
            target_index=binding[
                "target_index"
            ],

            source_face=binding[
                "source_face"
            ],

            source_triangle=binding[
                "source_triangle"
            ],

            source_vertices=tuple(
                binding["source_vertices"]
            ),

            barycentric=tuple(
                binding["barycentric"]
            ),
        )
        for binding in data["bindings"]
    ]

    # ---------------------------------------------------------
    # Optional snapshots
    # ---------------------------------------------------------

    source_snapshot = None
    target_snapshot = None

    if "source_snapshot" in data:

        source_snapshot = _snapshot_from_dict(
            data["source_snapshot"]
        )

    if "target_snapshot" in data:

        target_snapshot = _snapshot_from_dict(
            data["target_snapshot"]
        )

    # ---------------------------------------------------------
    # Topology map
    # ---------------------------------------------------------

    return TopologyMap(
        source_fingerprint=_fingerprint_from_dict(
            data["source_fingerprint"]
        ),

        target_fingerprint=_fingerprint_from_dict(
            data["target_fingerprint"]
        ),

        bindings=bindings,

        source_snapshot=source_snapshot,
        target_snapshot=target_snapshot,
    )