# type: ignore
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

import maya.cmds as cmds


ConstraintType = Literal[
    "parent",
    "point",
    "orient",
    "scale",
    "parent_scale",
    "aim",
]

@dataclass
class Constraint:
    """Base wrapper for Maya constraint nodes."""

    node: str
    driven: str
    drivers: list[str] = field(default_factory=list)

    # Override in subclasses.
    command_name: str = field(default="", init=False, repr=False)

    def _command(self):
        """Return the Maya command associated with this constraint."""
        return getattr(cmds, self.command_name)

    def refresh(self) -> None:
        """Refresh the stored driver list from Maya."""

        self.drivers = (
            self._command()(
                self.node,
                query=True,
                targetList=True,
            )
            or []
        )

    @property
    def weights(self) -> dict[str, str]:
        """Return driver names mapped to weight attribute plugs."""

        command = self._command()

        drivers = (
            command(
                self.node,
                query=True,
                targetList=True,
            )
            or []
        )

        aliases = (
            command(
                self.node,
                query=True,
                weightAliasList=True,
            )
            or []
        )

        return {
            driver: f"{self.node}.{alias}"
            for driver, alias in zip(
                drivers,
                aliases,
                strict=True,
            )
        }

    @property
    def connections(self) -> list[str]:
        """Return all constraint weight plugs."""
        return list(self.weights.values())

    def add_driver(
        self,
        driver: str,
        weight: float = 1.0,
    ) -> str:
        """Add another driver to this constraint."""

        _validate_transform(driver)
        self.refresh()

        if driver in self.drivers:
            cmds.warning(
                f"{driver} is already a driver of {self.node}."
            )
            return self.weights[driver]

        self._command()(
            driver,
            self.node,
            edit=True,
            weight=weight,
        )

        self.refresh()
        return self.weights[driver]

    def remove_driver(self, driver: str) -> None:
        """Remove a driver from this constraint."""

        self.refresh()

        if driver not in self.drivers:
            raise ValueError(
                f"{driver!r} is not a driver of {self.node!r}."
            )

        self._command()(
            driver,
            self.node,
            edit=True,
            remove=True,
        )

        self.refresh()

    def set_weight(
        self,
        driver: str,
        weight: float,
    ) -> None:
        """Set a driver's constraint weight."""

        weights = self.weights

        if driver not in weights:
            raise ValueError(
                f"{driver!r} is not a driver of {self.node!r}."
            )

        cmds.setAttr(weights[driver], weight)


@dataclass
class ParentConstraint(Constraint):
    """Wrapper around a Maya parentConstraint node."""

    command_name: str = field(
        default="parentConstraint",
        init=False,
        repr=False,
    )

@dataclass
class PointConstraint(Constraint):
    """Wrapper around a Maya pointConstraint node."""

    command_name: str = field(
        default="pointConstraint",
        init=False,
        repr=False,
    )

@dataclass
class OrientConstraint(Constraint):
    """Wrapper around a Maya orientConstraint node."""

    command_name: str = field(
        default="orientConstraint",
        init=False,
        repr=False,
    )


@dataclass
class ScaleConstraint(Constraint):
    """Wrapper around a Maya scaleConstraint node."""

    command_name: str = field(
        default="scaleConstraint",
        init=False,
        repr=False,
    )



def constraint(
    drivers: str | Sequence[str],
    driven: str,
    constraint_type: ConstraintType = "parent",
    parent: str | None = None,
    name: str | None = None,
    maintain_offset: bool = True,
    weight: float = 1.0,
    skip_translate: Sequence[str] | None = None,
    skip_rotate: Sequence[str] | None = None,
    skip_scale: Sequence[str] | None = None,
    **kwargs,
) -> Constraint | list[Constraint]:
    """Create one or more Maya constraints.

    Supported types:
        parent
        point
        orient
        scale
        parent_scale

    Returns:
        A Constraint wrapper, or a list of two wrappers
        for parent_scale.
    """

    driver_list = _normalize_drivers(drivers)

    _validate_transform(driven)

    if not driver_list:
        raise ValueError(
            "At least one driver must be provided."
        )

    # Combined parent + scale constraint.
    if constraint_type == "parent_scale":

        parent_constraint = _create_parent_constraint(
            drivers=driver_list,
            driven=driven,
            name=f"{name}_parentConstraint" if name else None,
            maintain_offset=maintain_offset,
            weight=weight,
            skip_translate=skip_translate,
            skip_rotate=skip_rotate,
        )

        scale_constraint = _create_scale_constraint(
            drivers=driver_list,
            driven=driven,
            name=f"{name}_scaleConstraint" if name else None,
            maintain_offset=maintain_offset,
            weight=weight,
            skip=skip_scale,
        )

        results = [
            parent_constraint,
            scale_constraint,
        ]

        if parent:
            for result in results:
                _organize_constraint(result.node, parent)

        return results

    creators = {
        "parent": _create_parent_constraint,
        "point": _create_point_constraint,
        "orient": _create_orient_constraint,
        "scale": _create_scale_constraint,
    }

    creator = creators.get(constraint_type)

    if creator is None:
        supported = ", ".join(
            sorted([*creators, "parent_scale"])
        )
        raise NotImplementedError(
            f"Constraint type {constraint_type!r} "
            f"is not implemented. "
            f"Currently supported: {supported}."
        )

    # Route axis options to the appropriate creator.
    if constraint_type == "parent":
        kwargs["skip_translate"] = skip_translate
        kwargs["skip_rotate"] = skip_rotate

    elif constraint_type == "point":
        kwargs["skip"] = skip_translate

    elif constraint_type == "orient":
        kwargs["skip"] = skip_rotate

    elif constraint_type == "scale":
        kwargs["skip"] = skip_scale

    result = creator(
        drivers=driver_list,
        driven=driven,
        name=name,
        maintain_offset=maintain_offset,
        weight=weight,
        **kwargs,
    )

    if parent:
        _organize_constraint(result.node, parent)

    return result



def _create_parent_constraint(
    drivers: list[str],
    driven: str,
    name: str | None = None,
    maintain_offset: bool = True,
    weight: float = 1.0,
    skip_translate: Sequence[str] | None = None,
    skip_rotate: Sequence[str] | None = None,
) -> ParentConstraint:
    """Create a parent constraint."""

    command_kwargs = {
        "maintainOffset": maintain_offset,
        "weight": weight,
    }

    if name:
        command_kwargs["name"] = name

    if skip_translate:
        command_kwargs["skipTranslate"] = list(skip_translate)

    if skip_rotate:
        command_kwargs["skipRotate"] = list(skip_rotate)

    return _create_constraint(
        drivers=drivers,
        driven=driven,
        wrapper_type=ParentConstraint,
        command=cmds.parentConstraint,
        command_kwargs=command_kwargs,
    )


def _create_orient_constraint(
    drivers: list[str],
    driven: str,
    name: str | None = None,
    maintain_offset: bool = True,
    weight: float = 1.0,
    skip: Sequence[str] | None = None,
) -> OrientConstraint:
    """Create an orient constraint."""

    command_kwargs = {
        "maintainOffset": maintain_offset,
        "weight": weight,
    }

    if name:
        command_kwargs["name"] = name

    if skip:
        command_kwargs["skip"] = list(skip)

    return _create_constraint(
        drivers=drivers,
        driven=driven,
        wrapper_type=OrientConstraint,
        command=cmds.orientConstraint,
        command_kwargs=command_kwargs,
    )

def _create_point_constraint(
    drivers: list[str],
    driven: str,
    name: str | None = None,
    maintain_offset: bool = True,
    weight: float = 1.0,
    skip: Sequence[str] | None = None,
) -> PointConstraint:
    """Create a Maya point constraint."""

    command_kwargs = {
        "maintainOffset": maintain_offset,
        "weight": weight,
    }

    if name:
        command_kwargs["name"] = name

    if skip:
        command_kwargs["skip"] = list(skip)

    return _create_constraint(
        drivers=drivers,
        driven=driven,
        wrapper_type=PointConstraint,
        command=cmds.pointConstraint,
        command_kwargs=command_kwargs,
    )


def _create_scale_constraint(
    drivers: list[str],
    driven: str,
    name: str | None = None,
    maintain_offset: bool = True,
    weight: float = 1.0,
    skip: Sequence[str] | None = None,
) -> ScaleConstraint:
    """Create a scale constraint."""

    command_kwargs = {
        "maintainOffset": maintain_offset,
        "weight": weight,
    }

    if name:
        command_kwargs["name"] = name

    if skip:
        command_kwargs["skip"] = list(skip)

    return _create_constraint(
        drivers=drivers,
        driven=driven,
        wrapper_type=ScaleConstraint,
        command=cmds.scaleConstraint,
        command_kwargs=command_kwargs,
    )


def _create_constraint(
    drivers: list[str],
    driven: str,
    wrapper_type: type[Constraint],
    command,
    command_kwargs: dict,
) -> Constraint:
    """Shared creation logic for supported constraints."""

    for driver in drivers:
        _validate_transform(driver)

    node = command(
        drivers,
        driven,
        **command_kwargs,
    )[0]

    result = wrapper_type(
        node=node,
        driven=driven,
        drivers=list(drivers),
    )

    result.refresh()
    return result


def _normalize_drivers(
    drivers: str | Sequence[str],
) -> list[str]:
    """Normalize one or multiple drivers."""

    if isinstance(drivers, str):
        return [drivers]

    return list(drivers)


def _validate_transform(node: str) -> None:
    """Ensure a Maya transform exists."""

    if not cmds.objExists(node):
        raise ValueError(
            f"Maya node does not exist: {node!r}"
        )


def _organize_constraint(
    constraint_node: str,
    parent: str,
    attribute: str = "constraintNodes",
) -> None:
    """Parent a Maya constraint node under a DAG transform."""

    _validate_transform(parent)
    cmds.parent(constraint_node, parent)



def get_constraint(
    node: str,
    driven: str | None = None,
) -> Constraint:
    """
    Wrap an existing Maya constraint node.

    Args:
        node:
            Name of an existing Maya constraint node.
        driven:
            Optional driven transform. If omitted, attempts
            to discover it from the constraint connections.

    Returns:
        The specialized Constraint wrapper.
    """

    if not cmds.objExists(node):
        raise ValueError(
            f"Constraint node does not exist: {node!r}"
        )

    constraint_types = {
        "parentConstraint": ParentConstraint,
        "orientConstraint": OrientConstraint,
        "scaleConstraint": ScaleConstraint,
        "pointConstraint": PointConstraint,
    }

    node_type = cmds.nodeType(node)
    wrapper_type = constraint_types.get(node_type)

    if wrapper_type is None:
        raise ValueError(
            f"Unsupported constraint type: {node_type!r}"
        )

    if driven is None:
        driven = _get_constraint_driven(node)

    _validate_transform(driven)

    result = wrapper_type(
        node=node,
        driven=driven,
    )

    result.refresh()

    return result


def _get_constraint_driven(node: str) -> str:
    """Find the transform driven by a Maya constraint."""

    node_type = cmds.nodeType(node)

    output_attributes = {
        "parentConstraint": [
            "constraintTranslateX",
            "constraintRotateX",
        ],
        "pointConstraint": [
            "constraintTranslateX",
        ],
        "orientConstraint": [
            "constraintRotateX",
        ],
        "scaleConstraint": [
            "constraintScaleX",
        ],
    }

    # Check direct output connections on every axis.
    for attribute in output_attributes[node_type]:
        base_attribute = attribute[:-1]

        for axis in "XYZ":
            plug = f"{node}.{base_attribute}{axis}"

            connections = cmds.listConnections(
                plug,
                source=False,
                destination=True,
                plugs=True,
            ) or []

            for connection in connections:
                driven = connection.split(".")[0]

                if cmds.nodeType(driven) in {
                    "transform",
                    "joint",
                }:
                    return driven

    # Fallback: the constrained transform often connects
    # its parentInverseMatrix to the constraint.
    parent_inverse = f"{node}.constraintParentInverseMatrix"

    if cmds.objExists(parent_inverse):
        connections = cmds.listConnections(
            parent_inverse,
            source=True,
            destination=False,
        ) or []

        for candidate in connections:
            if cmds.nodeType(candidate) in {
                "transform",
                "joint",
            }:
                return candidate

    raise ValueError(
        f"Could not determine the driven transform for "
        f"{node!r}. Pass driven explicitly to get_constraint()."
    )