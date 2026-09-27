from __future__ import annotations

import maya.cmds as cmds


def select_components(
    components: str | list[str],
) -> None:
    """Replace the current selection with components."""

    if not components:
        cmds.select(clear=True)
        return

    cmds.select(
        components,
        replace=True,
    )


def add_components_to_selection(
    components: str | list[str],
) -> None:
    """Add components to the current selection."""

    if not components:
        return

    cmds.select(
        components,
        add=True,
    )


def remove_components_from_selection(
    components: str | list[str],
) -> None:
    """Remove components from the current selection."""

    if not components:
        return

    cmds.select(
        components,
        deselect=True,
    )