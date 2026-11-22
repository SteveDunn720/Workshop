"""Capture a profile image from an existing Maya perspective model panel."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from maya import cmds


def _is_perspective(panel: str) -> bool:
    """Return True if this model panel currently displays a perspective camera."""
    try:
        camera = cmds.modelPanel(panel, query=True, camera=True)
        if not camera:
            return False
        shapes = cmds.listRelatives(camera, shapes=True, fullPath=True) or []
        shape = shapes[0] if shapes else camera
        return not bool(cmds.camera(shape, query=True, orthographic=True))
    except (RuntimeError, ValueError):
        return False


def perspective_panel() -> str:
    """Prefer the focused perspective panel, then visible perspective panels."""
    panels = []
    for panel in (
        cmds.getPanel(withFocus=True),
        cmds.getPanel(underPointer=True),
        *(cmds.getPanel(visiblePanels=True) or []),
    ):
        if panel and panel not in panels:
            panels.append(panel)
    for panel in panels:
        if cmds.getPanel(typeOf=panel) == 'modelPanel' and _is_perspective(panel):
            return panel
    raise RuntimeError('No visible perspective model panel found. Open a perspective viewport first.')


def capture_perspective_profile(target: Path, size: int = 512) -> Path:
    """Save the current perspective framing to a PNG without moving any cameras."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    panel = perspective_panel()

    with TemporaryDirectory(prefix='workshop_profile_') as temp:
        base = Path(temp) / 'profile'
        cmds.playblast(
            editorPanelName=panel,
            frame=[cmds.currentTime(query=True)],
            format='image',
            filename=str(base),
            viewer=False,
            compression='png',
            percent=100,
            widthHeight=(size, size),
            forceOverwrite=True,
            offScreen=True,
            showOrnaments=False,
            framePadding=0,
        )
        candidates = sorted(Path(temp).glob('profile*.png'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError('Maya did not create a PNG from the perspective viewport.')
        # Copy while the temporary directory still exists.
        from shutil import copyfile
        copyfile(candidates[0], target)
    return target
