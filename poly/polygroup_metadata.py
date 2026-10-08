from __future__ import annotations

import json

import maya.cmds as cmds


METADATA_PREFIX = "polygroupMetadata_"


def get_metadata_attr(
    uv_set: str,
) -> str:
    """Get the metadata attribute name for a PolyGroup UV set."""

    safe_name = uv_set.replace(":", "_")

    return f"{METADATA_PREFIX}{safe_name}"


def metadata_exists(
    mesh: str,
    uv_set: str,
) -> bool:
    """Check whether metadata exists for a PolyGroup layer."""

    attr = get_metadata_attr(
        uv_set=uv_set,
    )

    return cmds.attributeQuery(
        attr,
        node=mesh,
        exists=True,
    )


def get_polygroup_metadata(
    mesh: str,
    uv_set: str,
) -> dict:
    """Read PolyGroup metadata from a mesh."""

    attr = get_metadata_attr(
        uv_set=uv_set,
    )

    if not cmds.attributeQuery(
        attr,
        node=mesh,
        exists=True,
    ):
        return {
            "version": 1,
            "polygroups": {},
        }

    value = cmds.getAttr(
        f"{mesh}.{attr}"
    )

    if not value:
        return {
            "version": 1,
            "polygroups": {},
        }

    return json.loads(value)


def set_polygroup_metadata(
    mesh: str,
    uv_set: str,
    data: dict,
) -> None:
    """Write PolyGroup metadata to a mesh."""

    attr = get_metadata_attr(
        uv_set=uv_set,
    )

    if not cmds.attributeQuery(
        attr,
        node=mesh,
        exists=True,
    ):
        cmds.addAttr(
            mesh,
            longName=attr,
            dataType="string",
        )

    cmds.setAttr(
        f"{mesh}.{attr}",
        json.dumps(data),
        type="string",
    )


def set_polygroup_data(
    mesh: str,
    uv_set: str,
    index: int,
    name: str,
    color: tuple[float, float, float],
) -> None:
    """Store metadata for one PolyGroup."""

    data = get_polygroup_metadata(
        mesh=mesh,
        uv_set=uv_set,
    )

    data["polygroups"][str(index)] = {
        "name": name,
        "color": list(color),
    }

    set_polygroup_metadata(
        mesh=mesh,
        uv_set=uv_set,
        data=data,
    )


def get_polygroup_data(
    mesh: str,
    uv_set: str,
    index: int,
) -> dict | None:
    """Get metadata for one PolyGroup."""

    data = get_polygroup_metadata(
        mesh=mesh,
        uv_set=uv_set,
    )

    return data["polygroups"].get(
        str(index)
    )


def remove_polygroup_data(
    mesh: str,
    uv_set: str,
    index: int,
) -> None:
    """Remove metadata for one PolyGroup."""

    data = get_polygroup_metadata(
        mesh=mesh,
        uv_set=uv_set,
    )

    data["polygroups"].pop(
        str(index),
        None,
    )

    set_polygroup_metadata(
        mesh=mesh,
        uv_set=uv_set,
        data=data,
    )