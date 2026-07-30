from __future__ import annotations

import json
import os
from pathlib import Path

import maya.cmds as cmds

SNAPSHOT_CAMERA = "snapshot_cam"
SNAPSHOT_CAMERA_GROUP = "snapshot_cam_grp"
SNAPSHOT_SWIVEL = "snapshot_cam_swivel"
SNAPSHOT_TILT = "snapshot_cam_tilt"


def snapshot_camera_exists() -> bool:
    """Return whether the snapshot camera hierarchy already exists."""
    return cmds.objExists(SNAPSHOT_CAMERA_GROUP)


def delete_snapshot_camera() -> None:
    """Delete the snapshot camera hierarchy when it exists."""
    if snapshot_camera_exists():
        cmds.delete(SNAPSHOT_CAMERA_GROUP)


def create_snapshot_camera() -> str:
    """Create and return the snapshot camera transform."""
    delete_snapshot_camera()

    group = cmds.group(empty=True, name=SNAPSHOT_CAMERA_GROUP)
    swivel = cmds.group(empty=True, name=SNAPSHOT_SWIVEL, parent=group)
    tilt = cmds.group(empty=True, name=SNAPSHOT_TILT, parent=swivel)

    camera, _camera_shape = cmds.camera(name=SNAPSHOT_CAMERA)
    camera = cmds.rename(camera, SNAPSHOT_CAMERA)
    cmds.parent(camera, tilt)

    return camera


def auto_frame_camera(camera: str, obj: str) -> None:
    """Frame an existing object through the supplied camera."""
    if not cmds.objExists(obj):
        raise ValueError(f"Object does not exist: {obj}")

    cmds.lookThru(camera)
    cmds.viewFit(camera, obj)


def place_snapshot_camera(
    obj: str,
    swivel: float = 0.0,
    tilt: float = 0.0,
    focal_length: float = 35.0,
    orthographic: bool = False,
) -> str:
    """Create and position a snapshot camera around an object's bounds."""
    if not cmds.objExists(obj):
        raise ValueError(f"Object does not exist: {obj}")

    camera = create_snapshot_camera()
    bbox = cmds.exactWorldBoundingBox(obj)

    center = [
        (bbox[0] + bbox[3]) / 2.0,
        (bbox[1] + bbox[4]) / 2.0,
        (bbox[2] + bbox[5]) / 2.0,
    ]
    cmds.xform(SNAPSHOT_CAMERA_GROUP, worldSpace=True, translation=center)
    cmds.setAttr(f"{SNAPSHOT_SWIVEL}.rotateY", swivel)
    cmds.setAttr(f"{SNAPSHOT_TILT}.rotateX", tilt)

    shapes = cmds.listRelatives(camera, shapes=True) or []
    if not shapes:
        raise RuntimeError(f"Camera shape not found for: {camera}")
    camera_shape = shapes[0]

    size_x = bbox[3] - bbox[0]
    size_y = bbox[4] - bbox[1]
    size_z = bbox[5] - bbox[2]

    if orthographic:
        cmds.setAttr(f"{camera_shape}.orthographic", True)
        cmds.setAttr(f"{camera_shape}.orthographicWidth", max(size_x, size_y) * 1.2)
        cmds.setAttr(f"{camera}.translateZ", max(size_x, size_y, size_z) * 2.0)
    else:
        cmds.setAttr(f"{camera_shape}.orthographic", False)
        cmds.setAttr(f"{camera_shape}.focalLength", focal_length)
        auto_frame_camera(camera, obj)

    cmds.grid(toggle=False)
    return camera


def build_turntable(start: float, end: float) -> None:
    """Animate the snapshot swivel through one full rotation."""
    if not snapshot_camera_exists():
        raise RuntimeError("Snapshot camera does not exist.")

    attribute = f"{SNAPSHOT_SWIVEL}.rotateY"
    cmds.setKeyframe(attribute, time=start, value=0)
    cmds.setKeyframe(attribute, time=end, value=360)
    cmds.selectKey(attribute)
    cmds.keyTangent(inTangentType="linear", outTangentType="linear")


def export_camera_json(
    camera: str,
    path: str | os.PathLike[str],
    name: str = "camera_settings",
) -> Path:
    """Export the current snapshot camera settings to a JSON file."""
    if not cmds.objExists(camera):
        raise ValueError(f"Camera does not exist: {camera}")

    shapes = cmds.listRelatives(camera, shapes=True) or []
    if not shapes:
        raise RuntimeError(f"Camera shape not found for: {camera}")
    camera_shape = shapes[0]

    data = {
        "camera": camera,
        "group_translate": cmds.xform(
            SNAPSHOT_CAMERA_GROUP,
            query=True,
            worldSpace=True,
            translation=True,
        ),
        "swivel": cmds.getAttr(f"{SNAPSHOT_SWIVEL}.rotateY"),
        "tilt": cmds.getAttr(f"{SNAPSHOT_TILT}.rotateX"),
        "orthographic": cmds.getAttr(f"{camera_shape}.orthographic"),
    }

    if data["orthographic"]:
        data["orthographicWidth"] = cmds.getAttr(
            f"{camera_shape}.orthographicWidth"
        )
    else:
        data["focalLength"] = cmds.getAttr(f"{camera_shape}.focalLength")

    output_directory = Path(path)
    output_directory.mkdir(parents=True, exist_ok=True)
    file_path = output_directory / f"{name}.json"
    file_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return file_path


def take_snapshot(
    camera: str,
    path: str | os.PathLike[str],
    width: int = 512,
    height: int = 512,
    name: str = "snapshot",
) -> None:
    """Capture a single playblast frame as a PNG image."""
    output_directory = Path(path)
    output_directory.mkdir(parents=True, exist_ok=True)

    cmds.lookThru(camera)
    cmds.playblast(
        frame=[cmds.currentTime(query=True)],
        format="image",
        filename=str(output_directory / name),
        viewer=False,
        compression="png",
        percent=100,
        widthHeight=(width, height),
        forceOverwrite=True,
        offScreen=True,
        showOrnaments=False,
        framePadding=0,
    )


def take_playblast(
    camera: str,
    path: str | os.PathLike[str],
    start: float,
    end: float,
    width: int = 512,
    height: int = 512,
    name: str = "playblast",
) -> None:
    """Capture an image-sequence playblast through the supplied camera."""
    output_directory = Path(path)
    output_directory.mkdir(parents=True, exist_ok=True)

    cmds.lookThru(camera)
    cmds.playblast(
        startTime=start,
        endTime=end,
        format="image",
        filename=str(output_directory / name),
        viewer=False,
        compression="png",
        percent=100,
        widthHeight=(width, height),
        forceOverwrite=True,
        offScreen=True,
        showOrnaments=False,
    )