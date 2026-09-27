from __future__ import annotations

from dataclasses import dataclass

import maya.cmds as cmds

import json



MODULE_ATTR = "guideModules"
MODULE_NAME_ATTR = "module"
PART_NAME_ATTR = "part"

SETTINGS_ATTR = "settings"
RELATIONSHIPS_ATTR = "relationships"

@dataclass
class GuideModule:
    module: str
    part: str



def initialize_module_data(guide: str) -> None:
    """
    Ensure a guide has the compound multi attribute used
    to store module memberships.
    """

    if not cmds.objExists(guide):
        raise ValueError(
            f"Guide does not exist: {guide}"
        )

    if cmds.attributeQuery(
        MODULE_ATTR,
        node=guide,
        exists=True,
    ):
        return

    cmds.addAttr(
        guide,
        longName=MODULE_ATTR,
        attributeType="compound",
        numberOfChildren=4,
        multi=True,
    )

    cmds.addAttr(
        guide,
        longName=MODULE_NAME_ATTR,
        dataType="string",
        parent=MODULE_ATTR,
    )

    cmds.addAttr(
        guide,
        longName=PART_NAME_ATTR,
        dataType="string",
        parent=MODULE_ATTR,
    )

    cmds.addAttr(
        guide,
        longName=SETTINGS_ATTR,
        dataType="string",
        parent=MODULE_ATTR,
    )

    cmds.addAttr(
        guide,
        longName=RELATIONSHIPS_ATTR,
        dataType="string",
        parent=MODULE_ATTR,
    )



def get_modules(
    guide: str,
) -> list[GuideModule]:
    """
    Return all module memberships stored on a guide.
    """

    if not cmds.objExists(guide):
        raise ValueError(
            f"Guide does not exist: {guide}"
        )

    if not cmds.attributeQuery(
        MODULE_ATTR,
        node=guide,
        exists=True,
    ):
        return []

    indices = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}",
        multiIndices=True,
    ) or []

    modules = []

    for index in indices:
        module = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{MODULE_NAME_ATTR}"
        ) or ""

        part = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{PART_NAME_ATTR}"
        ) or ""

        if not module:
            continue

        modules.append(
            GuideModule(
                module=module,
                part=part,
            )
        )

    return modules



def add_module(
    guide: str,
    module: str,
    part: str,
) -> GuideModule:
    """
    Add a module membership to a guide.

    Duplicate module/part combinations are ignored.
    """

    initialize_module_data(guide)

    new_module = GuideModule(
        module=module,
        part=part,
    )

    existing = get_modules(guide)

    if new_module in existing:
        return new_module

    indices = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}",
        multiIndices=True,
    ) or []

    index = max(indices, default=-1) + 1

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{MODULE_NAME_ATTR}",
        module,
        type="string",
    )

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{PART_NAME_ATTR}",
        part,
        type="string",
    )

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{SETTINGS_ATTR}",
        "{}",
        type="string",
    )

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{RELATIONSHIPS_ATTR}",
        "{}",
        type="string",
    )

    return new_module


def remove_module(
    guide: str,
    module: str,
    part: str,
) -> bool:
    """
    Remove a specific module/part membership.

    Returns True if something was removed.
    """

    if not cmds.attributeQuery(
        MODULE_ATTR,
        node=guide,
        exists=True,
    ):
        return False

    indices = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}",
        multiIndices=True,
    ) or []

    for index in indices:

        module_value = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{MODULE_NAME_ATTR}"
        ) or ""

        part_value = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{PART_NAME_ATTR}"
        ) or ""

        if (
            module_value == module
            and part_value == part
        ):
            cmds.removeMultiInstance(
                f"{guide}.{MODULE_ATTR}[{index}]",
                b=True,
            )

            return True

    return False


def get_module_index(
    guide: str,
    module: str,
    part: str,
) -> int | None:

    if not cmds.attributeQuery(
        MODULE_ATTR,
        node=guide,
        exists=True,
    ):
        return None

    indices = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}",
        multiIndices=True,
    ) or []

    for index in indices:

        module_value = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{MODULE_NAME_ATTR}"
        ) or ""

        part_value = cmds.getAttr(
            f"{guide}.{MODULE_ATTR}[{index}].{PART_NAME_ATTR}"
        ) or ""

        if (
            module_value == module
            and part_value == part
        ):
            return index

    return None


def get_module_settings(
    guide: str,
    module: str,
    part: str,
) -> dict:

    index = get_module_index(
        guide,
        module,
        part,
    )

    if index is None:
        return {}

    value = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{SETTINGS_ATTR}"
    ) or "{}"

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def get_module_relationships(
    guide: str,
    module: str,
    part: str,
) -> dict:

    index = get_module_index(
        guide,
        module,
        part,
    )

    if index is None:
        return {}

    value = cmds.getAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{RELATIONSHIPS_ATTR}"
    ) or "{}"

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def set_module_setting(
    guide: str,
    module: str,
    part: str,
    setting: str,
    value,
) -> None:

    index = get_module_index(
        guide,
        module,
        part,
    )

    if index is None:
        raise ValueError(
            f"Module '{module} / {part}' "
            f"does not exist on '{guide}'"
        )

    settings = get_module_settings(
        guide,
        module,
        part,
    )

    settings[setting] = value

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{SETTINGS_ATTR}",
        json.dumps(settings),
        type="string",
    )


def set_module_relationship(
    guide: str,
    module: str,
    part: str,
    relationship: str,
    value,
) -> None:

    index = get_module_index(
        guide,
        module,
        part,
    )

    if index is None:
        raise ValueError(
            f"Module '{module} / {part}' "
            f"does not exist on '{guide}'"
        )

    relationships = get_module_relationships(
        guide,
        module,
        part,
    )

    relationships[relationship] = value

    cmds.setAttr(
        f"{guide}.{MODULE_ATTR}[{index}].{RELATIONSHIPS_ATTR}",
        json.dumps(relationships),
        type="string",
    )