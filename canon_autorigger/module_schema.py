from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModuleSetting:
    name: str
    setting_type: str
    default: Any = None


@dataclass
class ModuleRelationship:
    name: str
    relationship_type: str
    default: Any = None

@dataclass
class ModuleGuide:
    name: str
    parent: str | None = None
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    guide_type: str = "joint"

@dataclass
class ModuleGuideArray:
    name: str
    default_count: int = 3
    minimum_count: int = 1
    spacing: tuple[float, float, float] = (0.0, 5.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    guide_type: str = "joint"
    parented: bool = True

def get_setting(
    module_class,
    name: str,
) -> ModuleSetting | None:
    """
    Find a setting definition on a module class.
    """

    for setting in module_class.SETTINGS:
        if setting.name == name:
            return setting

    return None


def get_relationship(
    module_class,
    name: str,
) -> ModuleRelationship | None:
    """
    Find a relationship definition on a module class.
    """

    for relationship in module_class.RELATIONSHIPS:
        if relationship.name == name:
            return relationship

    return None


def get_setting_value(
    instance,
    module_class,
    name: str,
):
    """
    Get the effective setting value for a module instance.

    Instance overrides take priority over the module default.
    """

    if name in instance.settings:
        return instance.settings[name]

    setting = get_setting(
        module_class,
        name,
    )

    if setting is None:
        raise ValueError(
            f"Unknown setting '{name}' "
            f"for module '{instance.module}'"
        )

    return setting.default


def get_relationship_value(
    instance,
    module_class,
    name: str,
):
    """
    Get the effective relationship value for a module instance.

    Instance overrides take priority over the module default.
    """

    if name in instance.relationships:
        return instance.relationships[name]

    relationship = get_relationship(
        module_class,
        name,
    )

    if relationship is None:
        raise ValueError(
            f"Unknown relationship '{name}' "
            f"for module '{instance.module}'"
        )

    return relationship.default