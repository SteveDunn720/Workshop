from dataclasses import dataclass, asdict
import json

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