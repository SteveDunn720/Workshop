from dataclasses import dataclass, asdict
import json
from pathlib import Path

import maya.cmds as cmds

from Workshop.poly.uv_sets import get_uv_sets, create_uv_set
from Workshop.poly.uvs import faces_to_uv_shell, faces_to_uvs, fit_uvs_to_udim
from Workshop.poly.polygroups import (
    get_polygroup_layers_from_scene, initialize_polygroup,
    PolyGroupLayer, get_udim_from_index,
)

from .face import get_face_indices
from .polygroups import PolyGroup, PolyGroupLayer


@dataclass
class PolyGroupData:
    name: str
    index: int
    color: tuple[float, float, float]
    faces: list[int]


@dataclass
class PolyGroupLayerData:
    name: str
    uv_set: str
    polygroups: list[PolyGroupData]


def serialize_polygroup(
    polygroup: PolyGroup,
) -> PolyGroupData:
    """Serialize a polygroup."""

    return PolyGroupData(
        name=polygroup.name,
        index=polygroup.index,
        color=polygroup.color,
        faces=get_face_indices(
            polygroup.get_faces()
        ),
    )


def serialize_polygroup_layer(
    layer: PolyGroupLayer,
) -> PolyGroupLayerData:
    """Serialize a polygroup layer."""

    return PolyGroupLayerData(
        name=layer.name,
        uv_set=layer.uv_set,
        polygroups=[
            serialize_polygroup(polygroup)
            for polygroup in layer.polygroups
        ],
    )

def write_polygroup_layer(
    layer: PolyGroupLayer,
    file_path: str,
) -> None:
    """Write a polygroup layer to JSON."""

    data = serialize_polygroup_layer(
        layer=layer,
    )

    with open(
        file_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            asdict(data),
            file,
            indent=4,
        )

# Configure these to match your local rig-build workspace.
RIG_BUILD_DIRECTORY = r"C:\Users\sldun\Documents\maya\projects\rig_build"
CANNON_DIRECTORY = "canon_rigs"
CANNON_PROP_DIRECTORY = "canon_prop_rigs"


def polygroup_json_directory(rig_name: str, prop: bool = False) -> Path:
    """Default folder for a particular character or prop rig."""
    if not rig_name or rig_name in (".", "..") or Path(rig_name).name != rig_name:
        raise ValueError("rig_name must be a single directory name")
    category = CANNON_PROP_DIRECTORY if prop else CANNON_DIRECTORY
    return Path(RIG_BUILD_DIRECTORY) / category / rig_name / "polygroups"


def write_polygroup_layers(mesh: str, file_path: str) -> None:
    """Export all PG_ layers on a mesh to a single JSON file."""
    layers = get_polygroup_layers_from_scene(mesh)
    if not layers:
        raise RuntimeError(f"No polygroup layers found on {mesh!r}")
    face_count = int(cmds.polyEvaluate(mesh, face=True))
    data = {
        "version": 1,
        "mesh": mesh,
        "face_count": face_count,
        "layers": [asdict(serialize_polygroup_layer(layer)) for layer in layers],
    }
    destination = Path(file_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)


def read_polygroup_layers(
    mesh: str,
    file_path: str,
    overwrite: bool = False,
) -> list[PolyGroupLayer]:
    """Restore PG_ layers from JSON to a same-topology mesh.

    Existing UV sets are never replaced unless overwrite=True.
    No UV layout is restored: groups are rebuilt using face membership.
    """
    with open(file_path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("version") != 1 or not isinstance(data.get("layers"), list):
        raise ValueError("Unsupported polygroup JSON format/version")
    face_count = int(cmds.polyEvaluate(mesh, face=True))
    if data.get("face_count") != face_count:
        raise ValueError("Mesh face count differs from the saved JSON")
    layers_data = data["layers"]
    existing = set(get_uv_sets(mesh))
    seen = set()
    for layer in layers_data:
        uv_set = layer["uv_set"]
        if not uv_set.startswith("PG_") or uv_set in seen:
            raise ValueError(f"Invalid or duplicate polygroup UV set: {uv_set}")
        seen.add(uv_set)
        if uv_set in existing and not overwrite:
            raise RuntimeError(f"UV set already exists: {uv_set}. Use overwrite=True to replace it.")
        groups = layer["polygroups"]
        indices = [g["index"] for g in groups]
        if len(indices) != len(set(indices)) or any(not isinstance(i, int) or i < 0 for i in indices):
            raise ValueError(f"Invalid polygroup indices in {uv_set}")
        assigned = set()
        for group in groups:
            faces = group["faces"]
            if any(not isinstance(f, int) or f < 0 or f >= face_count for f in faces):
                raise ValueError(f"Invalid face indices in {uv_set}")
            if len(faces) != len(set(faces)) or assigned.intersection(faces):
                raise ValueError(f"Overlapping or repeated face assignments in {uv_set}")
            assigned.update(faces)
        if len(assigned) != face_count:
            raise ValueError(f"Incomplete face coverage in {uv_set}: {len(assigned)}/{face_count}")

    result = []
    previous_uv_set = (cmds.polyUVSet(mesh, q=True, currentUVSet=True) or [None])[0]
    try:
        for layer_data in layers_data:
            uv_set = layer_data["uv_set"]
            if uv_set in existing:
                cmds.polyUVSet(mesh, delete=True, uvSet=uv_set)
            create_uv_set(mesh, uv_set, initialize=True)
            layer = PolyGroupLayer(name=layer_data["name"], mesh=mesh, uv_set=uv_set)
            for group_data in layer_data["polygroups"]:
                group = initialize_polygroup(
                    layer=layer,
                    name=group_data["name"],
                    index=group_data["index"],
                    color=tuple(group_data["color"]),
                )
                faces = [f"{mesh}.f[{index}]" for index in group_data["faces"]]
                if faces:
                    faces_to_uv_shell(
                        faces=faces, uv_set=uv_set,
                        create_uv_set_if_missing=False, sew_interior=True,
                    )
                    uvs = faces_to_uvs(faces=faces, uv_set=uv_set)
                    fit_uvs_to_udim(uvs=uvs, udim=group.udim, uv_set=uv_set)
                group.apply_color()
            result.append(layer)
    finally:
        available = get_uv_sets(mesh)
        if previous_uv_set in available:
            cmds.polyUVSet(mesh, currentUVSet=True, uvSet=previous_uv_set)
    return result
