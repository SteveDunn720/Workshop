from __future__ import annotations

import builtins

from pathlib import Path

import maya.cmds as cmds

import random
import time

from Workshop.color.palette import (
    Palette,
    PaletteColor,
    RIG_PALETTE_FOLDER,
    load_palette,
    save_palette,
)


COLOR_CONTROL = "color_options_ctrl"

_RANDOM_COLOR_TIME_JOB: int | None = None
_RANDOM_COLOR_IDLE_JOB: int | None = None


def write_rig_color_palette(
    rig_palette_name: str,
    overwrite: bool = False,
) -> Path | None:
    """Write the current rig color setup to a rig palette JSON file.

    Args:
        rig_palette_name:
            Name of the rig palette.

        overwrite:
            If True, overwrite an existing palette with the same name.
            If False, leave the existing palette untouched.

    Returns:
        The path to the written palette.

        Returns None if the palette already exists and overwrite is False.

    Raises:
        RuntimeError:
            If color_options_ctrl does not exist.
    """

    if not cmds.objExists(COLOR_CONTROL):
        raise RuntimeError(
            f'"{COLOR_CONTROL}" does not exist.'
        )

    # Match the filename cleanup used by save_palette().
    filename = (
        rig_palette_name
        .strip()
        .lower()
        .replace(" ", "_")
    )

    if not filename.endswith(".json"):
        filename += ".json"

    output_path = (
        RIG_PALETTE_FOLDER
        / filename
    )

    # --------------------------------------------------------------
    # Existing palette check
    # --------------------------------------------------------------

    if output_path.exists() and not overwrite:
        cmds.warning(
            f'Rig palette "{rig_palette_name}" already exists. '
            "Palette was not overwritten."
        )

        return None

    # --------------------------------------------------------------
    # Find rig color types
    # --------------------------------------------------------------

    user_attributes = cmds.listAttr(
        COLOR_CONTROL,
        userDefined=True,
    ) or []

    rig_types: list[str] = []

    for attribute in user_attributes:

        if not attribute.endswith(
            "_color"
        ):
            continue

        plug = (
            f"{COLOR_CONTROL}.{attribute}"
        )

        attribute_type = cmds.getAttr(
            plug,
            type=True,
        )

        if attribute_type != "double3":
            continue

        rig_type = attribute.removesuffix(
            "_color"
        )

        rig_types.append(
            rig_type
        )

    # --------------------------------------------------------------
    # Build palette colors
    # --------------------------------------------------------------

    palette_colors: list[PaletteColor] = []

    for rig_type in rig_types:

        color_attr = (
            f"{COLOR_CONTROL}."
            f"{rig_type}_color"
        )

        draw_on_top_attr = (
            f"{COLOR_CONTROL}."
            f"{rig_type}_draw_on_top"
        )

        thickness_attr = (
            f"{COLOR_CONTROL}."
            f"{rig_type}_Thickness"
        )

        # Maya returns a double3 as:
        #
        # [(r, g, b)]
        #
        # so grab the first tuple.
        color_value = cmds.getAttr(
            color_attr
        )[0]

        rgb = (
            float(color_value[0]),
            float(color_value[1]),
            float(color_value[2]),
        )

        # These should exist for initialized rig colors,
        # but the checks make the writer tolerant of older setups.
        draw_on_top = (
            bool(
                cmds.getAttr(
                    draw_on_top_attr
                )
            )
            if cmds.objExists(
                draw_on_top_attr
            )
            else False
        )

        thickness = (
            float(
                cmds.getAttr(
                    thickness_attr
                )
            )
            if cmds.objExists(
                thickness_attr
            )
            else -1.0
        )

        palette_color = PaletteColor(
            name=rig_type,
            rig_type=rig_type,
            rgb=rgb,
            draw_on_top=draw_on_top,
            thickness=thickness,
        )

        palette_colors.append(
            palette_color
        )

    # --------------------------------------------------------------
    # Build + save palette
    # --------------------------------------------------------------

    palette = Palette(
        name=rig_palette_name,
        colors=palette_colors,
        is_rig_palette=True,
    )

    path = save_palette(
        palette
    )

    return path



def apply_rig_color_palette(
    rig_palette_name: str,
) -> None:
    """Apply a saved rig color palette to color_options_ctrl.

    Missing rig types on either the rig or palette are ignored.
    """

    if not cmds.objExists(COLOR_CONTROL):
        cmds.warning(
            f'"{COLOR_CONTROL}" does not exist.'
        )
        return

    try:
        palette = load_palette(
            rig_palette_name,
            rig_palette=True,
        )
    except FileNotFoundError:
        cmds.warning(
            f'Rig palette "{rig_palette_name}" does not exist.'
        )
        return

    for palette_color in palette.colors:
        rig_type = palette_color.rig_type

        if not rig_type:
            continue

        color_attr = (
            f"{COLOR_CONTROL}.{rig_type}_color"
        )

        draw_on_top_attr = (
            f"{COLOR_CONTROL}.{rig_type}_draw_on_top"
        )

        thickness_attr = (
            f"{COLOR_CONTROL}.{rig_type}_Thickness"
        )

        # ----------------------------------------------------------
        # Rig type does not exist on this rig
        # ----------------------------------------------------------

        if not cmds.objExists(
            color_attr
        ):
            continue

        # ----------------------------------------------------------
        # Color
        # ----------------------------------------------------------

        cmds.setAttr(
            color_attr,
            *palette_color.rgb,
            type="double3",
        )

        # ----------------------------------------------------------
        # Draw on top
        # ----------------------------------------------------------

        if cmds.objExists(
            draw_on_top_attr
        ):
            cmds.setAttr(
                draw_on_top_attr,
                palette_color.draw_on_top,
            )

        # ----------------------------------------------------------
        # Line width / thickness
        # ----------------------------------------------------------

        if cmds.objExists(
            thickness_attr
        ):
            cmds.setAttr(
                thickness_attr,
                palette_color.thickness,
            )


def randomize_rig_colors(
    undoable: bool = True,
) -> None:
    """Randomize all rig colors on color_options_ctrl.

    Draw-on-top and thickness values are left unchanged.

    Args:
        undoable:
            If True, color changes are added to Maya's undo history.
            If False, the changes are excluded from the undo queue.
    """

    if not cmds.objExists(COLOR_CONTROL):
        cmds.warning(
            f'"{COLOR_CONTROL}" does not exist.'
        )
        return

    user_attributes = cmds.listAttr(
        COLOR_CONTROL,
        userDefined=True,
    ) or []

    undo_was_enabled = cmds.undoInfo(
        query=True,
        state=True,
    )

    try:
        if not undoable:
            cmds.undoInfo(
                stateWithoutFlush=False
            )

        for attribute in user_attributes:
            if not attribute.endswith("_color"):
                continue

            plug = f"{COLOR_CONTROL}.{attribute}"

            if cmds.getAttr(
                plug,
                type=True,
            ) != "double3":
                continue

            color = (
                random.uniform(0.0, 1.0),
                random.uniform(0.0, 1.0),
                random.uniform(0.0, 1.0),
            )

            cmds.setAttr(
                plug,
                *color,
                type="double3",
            )

    finally:
        if not undoable:
            cmds.undoInfo(
                stateWithoutFlush=undo_was_enabled
            )



#####################################


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------

_STATE_NAME = "_WORKSHOP_RANDOM_RIG_COLOR_STATE"


def _get_random_color_state() -> dict:
    """Get persistent state for the current Maya session."""

    if not hasattr(builtins, _STATE_NAME):
        setattr(
            builtins,
            _STATE_NAME,
            {
                "mode": "off",
                "time_job": None,
                "idle_job": None,
                "last_idle_time": 0.0,
                "idle_interval": 0.15,
            },
        )

    return getattr(
        builtins,
        _STATE_NAME
    )


# ----------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------

def _randomize_on_time_change() -> None:
    """Randomize only if time mode is still active."""

    state = _get_random_color_state()

    if state["mode"] != "time":
        return

    randomize_rig_colors(undoable=False)


def _randomize_on_idle() -> None:
    """Randomize only if idle mode is still active."""

    state = _get_random_color_state()

    if state["mode"] != "idle":
        return

    randomize_rig_colors(undoable=False)


def _randomize_on_playback() -> None:
    """Randomize only while Maya is actively playing."""

    state = _get_random_color_state()

    if state["mode"] != "playback":
        return

    if not cmds.play(
        query=True,
        state=True,
    ):
        return

    randomize_rig_colors(undoable=False)


def _randomize_on_slow_idle() -> None:
    """Randomize periodically while Maya is idle."""

    state = _get_random_color_state()

    if state["mode"] != "slow_idle":
        return

    current_time = time.monotonic()

    elapsed = (
        current_time
        - state["last_idle_time"]
    )

    if elapsed < state["idle_interval"]:
        return

    state["last_idle_time"] = (
        current_time
    )

    randomize_rig_colors(undoable=False)


# ----------------------------------------------------------------------
# Job cleanup
# ----------------------------------------------------------------------

def disable_random_rig_color_jobs() -> None:
    """Kill all Workshop random-color jobs."""

    state = _get_random_color_state()

    # Set this FIRST so any callback already executing
    # immediately becomes harmless.
    state["mode"] = "off"

    for key in (
        "time_job",
        "idle_job",
    ):
        job_id = state[key]

        if (
            job_id is not None
            and cmds.scriptJob(
                exists=job_id
            )
        ):
            cmds.scriptJob(
                kill=job_id,
                force=True,
            )

        state[key] = None


# ----------------------------------------------------------------------
# Modes
# ----------------------------------------------------------------------

def enable_random_rig_colors_on_time_change() -> None:
    """Randomize whenever Maya's current time changes."""

    disable_random_rig_color_jobs()

    state = _get_random_color_state()

    state["mode"] = "time"

    state["time_job"] = cmds.scriptJob(
        event=[
            "timeChanged",
            _randomize_on_time_change,
        ],
        protected=True,
    )


def enable_random_rig_colors_on_idle() -> None:
    """Randomize continuously while Maya is idle."""

    disable_random_rig_color_jobs()

    state = _get_random_color_state()

    state["mode"] = "idle"

    state["idle_job"] = cmds.scriptJob(
        idleEvent=_randomize_on_idle,
        protected=True,
    )

def enable_random_rig_colors_on_playback() -> None:
    """Randomize colors only during Maya playback."""

    disable_random_rig_color_jobs()

    state = _get_random_color_state()

    state["mode"] = "playback"

    state["time_job"] = cmds.scriptJob(
        event=[
            "timeChanged",
            _randomize_on_playback,
        ],
        protected=True,
    )

def enable_random_rig_colors_on_slow_idle(
    interval: float = 0.15,
) -> None:
    """Randomize colors periodically while Maya is idle."""

    disable_random_rig_color_jobs()

    state = _get_random_color_state()

    state["mode"] = "slow_idle"
    state["idle_interval"] = interval
    state["last_idle_time"] = 0.0

    state["idle_job"] = cmds.scriptJob(
        idleEvent=_randomize_on_slow_idle,
        protected=True,
    )


def set_random_rig_color_mode(
    mode: str,
) -> None:
    """Set random rig color behavior.

    Modes:
        off
        time
        playback
        idle
        slow_idle
    """

    mode = mode.lower().strip()

    if mode == "off":
        disable_random_rig_color_jobs()

    elif mode == "time":
        enable_random_rig_colors_on_time_change()

    elif mode == "playback":
        enable_random_rig_colors_on_playback()

    elif mode == "idle":
        enable_random_rig_colors_on_idle()

    elif mode == "slow_idle":
        enable_random_rig_colors_on_slow_idle()

    else:
        raise ValueError(
            f"Unknown random color mode: {mode}"
        )

def get_random_rig_color_mode() -> str:
    """Return the currently active mode."""

    return _get_random_color_state()["mode"]