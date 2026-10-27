from __future__ import annotations

from maya import cmds

from Workshop.canon_autorigger.modules import get_module_class

from Workshop.guide.curve_gen import create_curve_guide
from Workshop.guide.module import add_module,  register_module_guide

from Workshop.guide.core import (
    GuideInfo,
    create_guide_from_position,
    create_spline_guide,
    read_guide,
)

from .module_schema import (
    ModuleGuide,
    ModuleGuideArray,
    ModuleCurveGuide,
    ModuleSplineGuide,
)
def create_module_guides(
    module: str,
    part: str,
    side: str = "M",
    guide_count: int | None = None,
    source_curve: str | None = None,
    duplicate: bool = True,
    spans: int | None = None,
    degree: int | None = None,
    length: float | None = None,
) -> list[GuideInfo]:
    """
    Create all guides required by a module.

    Supports:
        ModuleGuide
        ModuleGuideArray
        ModuleCurveGuide

    Curve modes:
        source_curve=None:
            Generate a new curve.

        source_curve provided, duplicate=True:
            Duplicate the source curve.

        source_curve provided, duplicate=False:
            Convert the original curve into a guide.
    """

    module_class = get_module_class(module)

    created_guides = []

    for definition in module_class.GUIDES:

        # -----------------------------------------
        # GUIDE ARRAY
        # -----------------------------------------

        if isinstance(definition, ModuleGuideArray):

            name = (
                part
                if len(module_class.GUIDES) == 1
                else f"{part}_{definition.name}"
            )

            count = (
                guide_count
                if guide_count is not None
                else definition.default_count
            )

            if count < definition.minimum_count:
                raise ValueError(
                    f"Module '{module}' requires at least "
                    f"{definition.minimum_count} guides."
                )

            created_guides.extend(
                _create_guide_array(
                    name=name,
                    side=side,
                    module=module,
                    part=part,
                    count=count,
                    spacing=definition.spacing,
                    rotation=definition.rotation,
                    guide_type=definition.guide_type,
                    parented=definition.parented,
                )
            )
        # -----------------------------------------
        # CURVE GUIDE
        # -----------------------------------------

        elif isinstance(definition, ModuleCurveGuide):

            if len(module_class.GUIDES) == 1:
                name = part
            else:
                name = f"{part}_{definition.name}"

            guide = _create_curve_guide(
                name=name,
                side=side,
                module=module,
                part=part,
                source_curve=source_curve,
                duplicate=duplicate,
                spans=(
                    definition.spans
                    if spans is None
                    else spans
                ),
                degree=(
                    definition.degree
                    if degree is None
                    else degree
                ),
                length=(
                    definition.length
                    if length is None
                    else length
                ),
            )

            created_guides.append(guide)
            
            register_module_guide(
                guide=guide.name,
                module_root=guide.name,
            )

            

        # -----------------------------------------
        # SINGLE GUIDE
        # -----------------------------------------

        elif isinstance(definition, ModuleGuide):

            if len(module_class.GUIDES) == 1:
                name = f"{part}_{side}"
            else:
                name = (
                    f"{part}_"
                    f"{definition.name}_"
                    f"{side}"
                )

            guide = _create_guide(
                name=name,
                position=definition.position,
                guide_type=definition.guide_type,
                module=module,
                part=part,
            )

            created_guides.append(guide)

            register_module_guide(
                guide=guide.name,
                module_root=guide.name,
            )

        # -----------------------------------------
        # SPLINE GUIDE
        # -----------------------------------------

        elif isinstance(definition, ModuleSplineGuide):

            # Use the module part to avoid naming conflicts.
            if len(module_class.GUIDES) == 1:
                name = part
            else:
                name = f"{part}_{definition.name}"

            lower_pos = definition.position

            spline_length = (
                definition.length
                if length is None
                else length
            )

            upper_pos = (
                lower_pos[0],
                lower_pos[1] + spline_length,
                lower_pos[2],
            )

            spline = create_spline_guide(
                parent="guides",
                lower_name=f"{name}_lower",
                upper_name=f"{name}_upper",
                curve_name=name,
                side=side,
                position=[
                    upper_pos,
                    lower_pos,
                ],
            )

            # Register the spline's curve as the module root.
            add_module(
                spline.curve.name,
                module=module,
                part=part,
            )

            # Keep one root guide per spline module.
            # The other components are resolved during build.
            created_guides.append(spline.curve)

            module_root = spline.curve.name

            for guide in (
                spline.curve,
                spline.lower,
                spline.lower_tan,
                spline.upper,
                spline.upper_tan,
            ):
                register_module_guide(
                    guide=guide.name,
                    module_root=module_root,
                )

        else:
            raise TypeError(
                f"Unsupported guide definition: "
                f"{type(definition).__name__}"
            )

    # Re-read the final guide metadata.
    return [
        read_guide(guide.name)
        for guide in created_guides
    ]

def _create_guide(
    name: str,
    position: tuple[float, float, float],
    guide_type: str,
    module: str,
    part: str,
) -> GuideInfo:
    """
    Create a single guide and register its module metadata.
    """

    guide = create_guide_from_position(
        pos=position,
        guide_name=name,
        parent="guides",
    )

    add_module(
        guide=guide.name,
        module=module,
        part=part,
    )

    return read_guide(guide.name)


def _create_guide_array(
    name: str,
    side: str,
    module: str,
    part: str,
    count: int,
    spacing: tuple[float, float, float],
    rotation: tuple[float, float, float],
    guide_type: str = "joint",
    parented: bool = True,
) -> list[GuideInfo]:
    """
    Create an array of guides.

    The first guide owns the module settings.
    All subsequent guides reference that module root.

    When parented=True, guides form a hierarchy.
    Otherwise, they are siblings under 'guides'.
    """

    created_guides = []
    previous_guide = None
    module_root = None

    for index in range(count):

        guide_name = f"{name}_{index:02d}_{side}"

        position = tuple(
            component * index
            for component in spacing
        )

        parent = (
            previous_guide
            if parented and previous_guide
            else "guides"
        )

        guide = create_guide_from_position(
            pos=position,
            guide_name=guide_name,
            parent=parent,
        )

        if module_root is None:
            module_root = guide.name

            add_module(
                guide=module_root,
                module=module,
                part=part,
            )

        register_module_guide(
            guide=guide.name,
            module_root=module_root,
        )

        created_guides.append(
            read_guide(guide.name)
        )

        previous_guide = guide.name

    return created_guides

def _create_curve_guide(
    name: str,
    side: str,
    module: str,
    part: str,
    source_curve: str | None = None,
    duplicate: bool = True,
    spans: int = 3,
    degree: int = 3,
    length: float = 10.0,
) -> GuideInfo:
    """Create a curve guide and register its module metadata."""

    guide_name = f"{name}_{side}_guide"

    guide = create_curve_guide(
        name=name,
        side=side,
        spans=spans,
        degree=degree,
        length=length,
        source_curve=source_curve,
        duplicate=duplicate,
    )

    # The curve generator may return None even when
    # the Maya curve was successfully created.
    if guide is None:
        if not cmds.objExists(guide_name):
            raise RuntimeError(
                f"Curve guide was not created: {guide_name}"
            )

        guide = read_guide(guide_name)

    elif isinstance(guide, str):
        guide = read_guide(guide)

    # Register the module on the created guide.
    add_module(
        guide.name,
        module=module,
        part=part,
    )

    return read_guide(guide.name)