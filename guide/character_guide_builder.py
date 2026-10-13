"""First-pass Workshop character guide builder (Maya Python).

Requires Workshop.guide.core.create_guide_from_position/create_spline_guide,
Workshop.guide.placement.solve.solve_position, and
Workshop.guide.placement.limb.orient_limb_guides.

Create all independent guides in world space, orient, then parent while
preserving world matrices. Spline endpoints are created by the spline builder.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from maya import cmds

from Workshop.guide.core import create_guide_from_position, create_spline_guide
from Workshop.guide.placement.structs import GuidePlacement
from Workshop.guide.placement.solve import solve_position
from Workshop.guide.placement.limb import orient_limb_guides


from pathlib import Path

DEFAULT_CONFIG = (
    Path(__file__).resolve().parent
    / "character_configs"
    / "character_guide_config_v1.json"
)


@dataclass
class GuideBuildResult:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    missing_regions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    splines: dict = field(default_factory=dict)


def _guide_name(name: str) -> str:
    return name if name.endswith('_guide') else f'{name}_guide'


def _position(node: str) -> tuple[float, float, float]:
    return tuple(cmds.xform(node, query=True, worldSpace=True, translation=True))


def _world_matrix(node: str) -> list[float]:
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def _parent_preserve_world(child: str, parent: str) -> None:
    """Use Workshop's joint-aware parenting for guide joints."""
    if not cmds.objExists(child) or not cmds.objExists(parent):
        raise RuntimeError(f'Cannot parent {child} -> {parent}: missing node')
    if cmds.listRelatives(child, parent=True):
        current = cmds.listRelatives(child, parent=True)[0]
        if current == parent:
            return
    # Maya's parent command preserves world transforms by default for joints,
    # but may insert transforms. Workshop's clean_parent handles jointOrient.
    from Workshop.transform.utils import clean_parent
    clean_parent(transform=child, parent=parent, joint_orient=True)


def _load_config(config: str | Path | dict) -> dict:
    if isinstance(config, dict):
        return config
    with open(config, 'r', encoding='utf-8') as stream:
        return json.load(stream)


def _resolve_positions(
    config: dict,
    mesh: str,
    uv_set: str,
    *,
    allow_reference_fallback: bool,
    result: GuideBuildResult,
) -> dict[str, tuple[float, float, float]]:
    """Resolve independent positions; match_parent is resolved later."""
    positions = {}
    for entry in config.get('guides', []):
        name = _guide_name(entry['name'])
        placement = entry['placement']
        method = placement['method']
        if method == 'match_parent':
            continue
        if method == 'origin':
            positions[name] = (0.0, 0.0, 0.0)
        elif method == 'region':
            region = placement['region']
            try:
                pos = solve_position(
                    GuidePlacement(name=entry['name'], region=region),
                    mesh=mesh,
                    uv_set=uv_set,
                )
                positions[name] = tuple(pos)
            except (LookupError, KeyError, ValueError, RuntimeError) as exc:
                result.missing_regions.append(f'{name}: {region} ({exc})')
                if allow_reference_fallback and 'reference_position' in entry:
                    positions[name] = tuple(entry['reference_position'])
                else:
                    raise RuntimeError(
                        f'Failed to resolve region {region!r} for {name}. '
                        'Fix the polygroup or use allow_reference_fallback=True.'
                    ) from exc
        else:
            raise ValueError(f'Unsupported placement method: {method} ({name})')
    return positions


def _resolve_match_parent_positions(config: dict, positions: dict) -> None:
    """Resolve matches recursively, even when entries are not parent-first."""
    pending = {
        _guide_name(entry['name']): entry
        for entry in config.get('guides', [])
        if entry['placement']['method'] == 'match_parent'
    }
    while pending:
        progressed = False
        for name, entry in list(pending.items()):
            parent = entry['placement'].get('parent') or entry.get('parent')
            if parent in positions:
                positions[name] = positions[parent]
            elif parent and cmds.objExists(parent):
                positions[name] = _position(parent)
            else:
                continue
            del pending[name]
            progressed = True
        if not progressed:
            raise RuntimeError(
                f'Unresolved match_parent positions: {list(pending)}. '
                'Check parent names and spline ownership.'
            )


def _validate_config(config: dict) -> None:
    names = [_guide_name(item['name']) for item in config.get('guides', [])]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate regular guide names in configuration')
    if not config.get('splines'):
        return
    generated = set()
    for spline in config['splines']:
        for part in ('lower_name', 'upper_name'):
            generated.add(_guide_name(f"{spline[part]}_{spline.get('side', 'M')}"))
    overlap = set(names) & generated
    if overlap:
        raise ValueError(f'Spline endpoints also listed as regular guides: {sorted(overlap)}')


def build_character_guides(
    config: str | Path | dict | None = None,
    mesh: str | None = None,
    uv_set: str | None = None,
    *,
    allow_reference_fallback: bool = False,
    dry_run: bool = False,
    orient: bool = True,
) -> GuideBuildResult:
    """Build a first-pass guide hierarchy from a JSON config.

    Run in an empty guide scene. Existing guide nodes are reused, not replaced.
    dry_run validates placement without creating guides.
    """
    if config is None:
        config = DEFAULT_CONFIG
    config = _load_config(config)
    _validate_config(config)
    mesh = mesh or config['mesh']
    uv_set = uv_set or config.get('uv_set', 'PG_Guides')
    result = GuideBuildResult()

    if not cmds.objExists(mesh):
        raise RuntimeError(f'Mesh does not exist: {mesh}')

    positions = _resolve_positions(
        config, mesh, uv_set,
        allow_reference_fallback=allow_reference_fallback,
        result=result,
    )
    _resolve_match_parent_positions(config, positions)

    # Resolve compound spline endpoint positions from their declared anchors.
    spline_positions = []
    for spline in config.get('splines', []):
        anchors = []
        for key in ('lower_placement', 'upper_placement'):
            placement = spline[key]
            if placement['method'] != 'match_parent':
                raise ValueError(f"Only match_parent spline anchors supported in v1: {spline['name']}")
            parent = placement['parent']
            if parent in positions:
                anchors.append(positions[parent])
            elif cmds.objExists(parent):
                anchors.append(_position(parent))
            else:
                raise RuntimeError(f"Missing spline anchor {parent!r} for {spline['name']}")
        spline_positions.append((spline, anchors[0], anchors[1]))

    if dry_run:
        print(f'[Workshop] Dry run: {len(positions)} regular guides, '
              f'{len(spline_positions)} splines, '
              f'{len(result.missing_regions)} unresolved regions.')
        for missing in result.missing_regions:
            print(f'  REGION FALLBACK: {missing}')
        return result

    if not cmds.objExists('guides'):
        cmds.group(empty=True, world=True, name='guides')

    # Create guides unparented (under a world-space holder), so orientation
    # operations cannot move descendants. Parent in the final pass.
    holder = cmds.group(empty=True, world=True, name='guide_build_temp#')
    try:
        for entry in config.get('guides', []):
            name = _guide_name(entry['name'])
            if cmds.objExists(name):
                result.existing.append(name)
                continue
            info = create_guide_from_position(
                pos=positions[name],
                guide_name=entry['name'],
                parent=holder,
            )
            created = info.name
            if created != name:
                raise RuntimeError(f'Expected {name}, builder returned {created}')
            result.created.append(name)

        # Spline creation owns endpoint/tangent guides and curve.
        # It is deliberately built after its independent anchor guides.
        for spline, lower_pos, upper_pos in spline_positions:
            lower_name = _guide_name(f"{spline['lower_name']}_{spline.get('side', 'M')}")
            upper_name = _guide_name(f"{spline['upper_name']}_{spline.get('side', 'M')}")
            if cmds.objExists(lower_name) or cmds.objExists(upper_name):
                raise RuntimeError(
                    f'Spline {spline["name"]}: endpoints already exist; '
                    'build in a clean scene or remove the previous spline first.'
                )
            info = create_spline_guide(
                parent=holder,
                lower_name=spline['lower_name'],
                upper_name=spline['upper_name'],
                curve_name=spline.get('curve_name', spline['name']),
                side=spline.get('side', 'M'),
                position=[upper_pos, lower_pos],  # Workshop API expects upper first
            )
            result.splines[spline['name']] = info

        # Orient independent chains before final parenting.
        if orient:
            for group in config.get('orientation_groups', []):
                chain = group['chain']
                if not all(cmds.objExists(node) for node in chain):
                    result.warnings.append(f"Skipped orientation: {group['name']} (missing guide)")
                    continue
                orient_limb_guides(
                    guides=chain,
                    aim_axis=group.get('aim_axis', 'y'),
                    up_axis=group.get('up_axis', 'z'),
                )

        # Parent regular guides in dependency order. For splines, their
        # endpoint guides are handled below; tangent parents stay as built.
        pending = { _guide_name(e['name']): e['parent'] for e in config.get('guides', []) }
        while pending:
            progressed = False
            for child, parent in list(pending.items()):
                if parent not in pending and cmds.objExists(parent):
                    _parent_preserve_world(child, parent)
                    del pending[child]
                    progressed = True
            if not progressed:
                raise RuntimeError(f'Unresolved hierarchy: {pending}')

        for spline, _, _ in spline_positions:
            side = spline.get('side', 'M')
            lower = _guide_name(f"{spline['lower_name']}_{side}")
            upper = _guide_name(f"{spline['upper_name']}_{side}")
            _parent_preserve_world(lower, spline['lower_parent'])
            _parent_preserve_world(upper, spline['upper_parent'])
            # Curve itself stays under the guides root, independent of endpoint parents.
            curve = _guide_name(f"{spline.get('curve_name', spline['name'])}_{side}")
            if cmds.objExists(curve):
                _parent_preserve_world(curve, 'guides')

        print(f'[Workshop] Built {len(result.created)} regular guides, '
              f'{len(result.splines)} splines. '
              f'{len(result.missing_regions)} region fallbacks.')
        return result
    finally:
        if cmds.objExists(holder):
            # Never delete generated guides if a build failed mid-way.
            remaining = cmds.listRelatives(holder, children=True) or []
            if remaining:
                cmds.parent(remaining, 'guides', absolute=True)
            cmds.delete(holder)
