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
from Workshop.guide.placement.force_planar import force_planar_guides
from Workshop.guide.placement.foot_roll import build_foot_roll_guides
from Workshop.guide.placement.head import head_guide_positions, style_head_guides

DEFAULT_CONFIG = Path(__file__).resolve().parent / "character_configs" / "character_guide_config_v1.json"


@dataclass
class GuideBuildResult:
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
    missing_regions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    splines: dict = field(default_factory=dict)
    flip_groups: list[str] = field(default_factory=list)
    curves: dict[str, str] = field(default_factory=dict)


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


def _side(name: str) -> str | None:
    if '_L_' in name:
        return 'L'
    if '_R_' in name:
        return 'R'
    return None


def _category(name: str) -> str | None:
    stem = name.lower()
    if any(word in stem for word in ('upperleg_', 'knee_', 'foot_', 'toe_', 'heel_', 'bank', 'toeball_', 'footroll_')):
        return 'legs'
    if any(word in stem for word in ('clav_', 'shoulder_', 'elbow_', 'hand_', 'finger_')):
        return 'arms'
    if any(word in stem for word in ('eye_', 'face_', 'jaw_', 'brow_', 'cheek_', 'nose_', 'mouth_', 'lip_', 'ear_', 'tongue_', 'nl_fold_', 'arch_')):
        return 'face'
    return None


def _mirror_enabled(category: str | None, symmetry: dict) -> bool:
    if not category:
        return False
    if symmetry.get('full', False):
        return True
    return bool(symmetry.get('parts', {}).get(category, False))


def _reflect_x(position):
    return (-position[0], position[1], position[2])


def _set_big_guide(name: str, radius: float = 5.0) -> None:
    if not cmds.objExists(name) or cmds.nodeType(name) != 'joint':
        return
    cmds.setAttr(f'{name}.radius', radius)
    cmds.setAttr(f'{name}.drawStyle', 3)


def _flip_group_name(category: str, side: str) -> str:
    return {'arms': 'arm', 'legs': 'leg', 'face': 'face'}[category] + f'_{side}_flip'


def _make_flip_group(category: str, side: str, parent: str) -> str:
    """Create at WORLD origin; parent without moving, flip only at the end."""
    name = _flip_group_name(category, side)
    if cmds.objExists(name):
        raise RuntimeError(f'Flip group already exists: {name}; use a clean guide scene')
    group = cmds.group(empty=True, world=True, name=name)
    _parent_preserve_world(group, parent)
    return group


def _resolve_positions(
    config: dict,
    mesh: str,
    uv_set: str,
    *,
    allow_reference_fallback: bool,
    result: GuideBuildResult,
    skip_regions: set[str] | None = None,
) -> dict[str, tuple[float, float, float]]:
    """Resolve independent positions; match_parent is resolved later."""
    positions = {}
    for entry in config.get('guides', []):
        name = _guide_name(entry['name'])
        placement = entry['placement']
        method = placement['method']
        if method in ('match_parent', 'procedural_head'):
            continue
        if name in (skip_regions or set()):
            continue
        if method == 'origin':
            positions[name] = (0.0, 0.0, 0.0)
        elif method == 'region':
            region = placement['region']
            try:
                pos = solve_position(
                    GuidePlacement(name=entry['name'], region=region),
                    mesh=mesh,
                    uv_set=placement.get('uv_set', config.get('polygroup_layers', {}).get(placement.get('layer', 'body'), uv_set)),
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


def _style_curve_guide(curve: str) -> None:
    """Keep all visible NURBS curve shapes on top of shaded geometry."""
    for shape in cmds.listRelatives(curve, shapes=True, fullPath=True) or []:
        if cmds.nodeType(shape) != 'nurbsCurve':
            continue
        plug = f'{shape}.alwaysDrawOnTop'
        if cmds.objExists(plug):
            cmds.setAttr(plug, 1)


def _parent_curve_guide(curve: str, parent: str) -> None:
    """Parent curve transform without altering its world-space shape."""
    if not cmds.objExists(parent):
        raise RuntimeError(f'{curve}: missing curve parent {parent!r}')
    if curve == parent:
        raise ValueError(f'{curve}: cannot parent curve to itself')
    current = cmds.listRelatives(curve, parent=True, fullPath=True) or []
    if current and cmds.ls(current[0], long=True)[0] == cmds.ls(parent, long=True)[0]:
        return
    cmds.parent(curve, parent, absolute=True)


def _build_curve_guides(config: dict, mesh: str, result: GuideBuildResult) -> None:
    """Create independent facial curves after guide hierarchy and flips are built."""
    from Workshop.poly.polygroup_boundary import create_polygroup_boundary_curve
    from Workshop.nurbs.curve import (
        create_curve_through_positions,
        reverse_curve,
    )

    curve_cfg = config.get('curve_guides', {})
    if not curve_cfg.get('enabled', False):
        return

    for entry in curve_cfg.get('curves', []):
        name = _guide_name(entry['name'])
        if cmds.objExists(name):
            _parent_curve_guide(name, entry.get('parent', 'head_root_M_guide'))
            _style_curve_guide(name)
            result.existing.append(name)
            result.curves[name] = name
            continue

        method = entry['method']
        uv_set = entry.get('uv_set', config.get('polygroup_layers', {}).get(
            entry.get('layer', 'face'), config.get('uv_set', 'PG_Guides')
        ))
        degree = entry.get('degree', 3)

        if method == 'polygroup_boundary':
            curve = create_polygroup_boundary_curve(
                mesh=entry.get('mesh', mesh),
                uv_set=uv_set,
                region_a=entry['region_a'],
                region_b=entry['region_b'],
                name=name,
                degree=degree,
                spans=entry.get('spans', 8),
                direction=(
                    'preserve' if entry.get('direction') in ('preserve', 'as_built')
                    else 'outward'
                ),
            )
        elif method == 'region_points':
            regions = entry['regions']
            if len(regions) < degree + 1:
                raise ValueError(
                    f'{name}: need at least {degree + 1} regions for degree {degree}'
                )
            points = [tuple(solve_position(
                GuidePlacement(name=f'{name}_{i}', region=region),
                mesh=entry.get('mesh', mesh),
                uv_set=uv_set,
            )) for i, region in enumerate(regions)]
            if 'spans' in entry:
                raise ValueError(
                    f'{name}: region_points does not support spans/resampling'
                )
            curve_mode = entry.get('curve_mode', 'cv')
            if curve_mode == 'interpolate':
                curve = create_curve_through_positions(
                    name=name,
                    positions=points,
                    degree=degree,
                )
            elif curve_mode == 'cv':
                curve = cmds.curve(name=name, degree=degree, point=points)
            else:
                raise ValueError(
                    f'{name}: unknown curve_mode {curve_mode!r}; '
                    'expected interpolate or cv'
                )
        else:
            raise ValueError(f'{name}: unknown curve method {method!r}')

        # Orient open curves from the center line outwards, by default.
        direction = entry.get('direction', 'outward_x')
        if direction == 'outward_x':
            cvs = cmds.ls(f'{curve}.cv[*]', flatten=True) or []
            if len(cvs) >= 2:
                start_x = cmds.pointPosition(cvs[0], world=True)[0]
                end_x = cmds.pointPosition(cvs[-1], world=True)[0]
                if abs(start_x) > abs(end_x):
                    reverse_curve(curve)
        elif direction == 'reverse':
            reverse_curve(curve)
        elif direction not in ('as_built', 'preserve'):
            raise ValueError(f'{name}: unknown direction {direction!r}')

        parent = entry.get('parent', 'head_root_M_guide')
        _parent_curve_guide(curve, parent)
        _style_curve_guide(curve)
        result.created.append(name)
        result.curves[name] = curve



def _build_eyeball_guides(config: dict, result: GuideBuildResult) -> None:
    """Place eye pivots from equator curves, then parent diameter curves.

    Eye curves must have been built by _build_curve_guides first. Existing
    pivot/look guides are reused, but newly created guides use Workshop tags.
    """
    eye_cfg = config.get('eyeball_guides', {})
    if not eye_cfg.get('enabled', False):
        return

    head_start = eye_cfg.get('head_start', 'head_root_M_guide')
    head_end = eye_cfg.get('head_end', 'head_ee_M_guide')
    if not cmds.objExists(head_start) or not cmds.objExists(head_end):
        raise RuntimeError('Eye look placement requires head start/end guides')
    a = _position(head_start)
    b = _position(head_end)
    head_length = sum((b[i] - a[i]) ** 2 for i in range(3)) ** 0.5
    if head_length <= 0:
        raise RuntimeError('Cannot calculate eye look offset from zero head length')
    look_distance = head_length * eye_cfg.get('look_distance_factor', 1.0)
    parent = eye_cfg.get('parent', 'head_root_M_guide')
    if not cmds.objExists(parent):
        raise RuntimeError(f'Missing eyeball guide parent: {parent}')

    for side in eye_cfg.get('sides', ['L', 'R']):
        equator = f'eyeball_{side}_guide'
        if not cmds.objExists(equator):
            raise RuntimeError(f'Missing eyeball equator curve: {equator}')

        # Bounding-box midpoint is the sphere center for a centered circular
        # equator loop; use it before parenting any eye curves.
        bbox = cmds.exactWorldBoundingBox(equator)
        center_pos = tuple((bbox[i] + bbox[i + 3]) * 0.5 for i in range(3))
        center = f'eye_center_{side}_guide'
        look = f'eye_look_{side}_guide'

        if not cmds.objExists(center):
            info = create_guide_from_position(
                pos=center_pos,
                guide_name=f'eye_center_{side}',
                parent=None,
            )
            if info.name != center:
                raise RuntimeError(f'Unexpected eye center guide: {info.name}')
            result.created.append(center)
        else:
            result.existing.append(center)
        _parent_preserve_world(center, parent)

        # Parent each measured loop beneath the center pivot without moving it.
        for curve in (equator, f'iris_{side}_guide', f'pupil_{side}_guide'):
            if not cmds.objExists(curve):
                raise RuntimeError(f'Missing eye diameter curve: {curve}')
            _parent_curve_guide(curve, center)
            _style_curve_guide(curve)

        if not cmds.objExists(look):
            info = create_guide_from_position(
                pos=(center_pos[0], center_pos[1], center_pos[2] + look_distance),
                guide_name=f'eye_look_{side}',
                parent=None,
            )
            if info.name != look:
                raise RuntimeError(f'Unexpected eye look guide: {info.name}')
            result.created.append(look)
        else:
            result.existing.append(look)
        _parent_preserve_world(look, center)

def _build_chest_corrective_guides(
    config: dict,
    mesh: str,
    result: GuideBuildResult,
    symmetry: dict,
) -> None:
    """Build chest correctives beneath root, with one optional mirrored side."""
    cfg = config.get('corrective_guides', {})
    if not cfg.get('enabled', False):
        return

    parent = cfg.get('parent', 'root_M_guide')
    group_name = cfg.get('group', 'corrective_guides')
    if not cmds.objExists(parent):
        raise RuntimeError(f'Missing corrective parent: {parent}')
    if not cmds.objExists(group_name):
        cmds.group(empty=True, world=True, name=group_name)
        result.created.append(group_name)
    _parent_preserve_world(group_name, parent)

    direction = symmetry.get('direction', 'L_to_R')
    source_side, target_side = direction.split('_to_')
    # This explicit part flag overrides symmetry.full for correctives.
    mirror = bool(symmetry.get('parts', {}).get('correctives', False))
    uv_set = cfg.get('uv_set', config.get('polygroup_layers', {}).get('face', 'PG_Face_Guides'))
    region_mesh = cfg.get('mesh', mesh)
    if not cmds.objExists(region_mesh):
        raise RuntimeError(f'Missing corrective mesh: {region_mesh}')

    from Workshop.guide.placement.ik_correctives_orient import orient_ik_correctives

    # Pec and trap inserts are distinct guides, but may share a placement region.
    parts = cfg.get('parts', [
        'pec_01', 'pec_02', 'pec_insert', 'trap_01',
        'trap_02', 'trap_insert', 'necktrap_insert', 'necktrap_01',
    ])
    region_overrides = cfg.get('region_overrides', {})
    positions = {}
    for side in (source_side, target_side):
        for part in parts:
            name = f'{part}_{side}_guide'
            if side == target_side and mirror:
                # Stage at source coordinates; the flip group reflects once.
                positions[name] = positions[f'{part}_{source_side}_guide']
                continue
            region = region_overrides.get(part, f'{part}_{{side}}').format(side=side)
            pos = tuple(solve_position(
                GuidePlacement(name=name, region=region),
                mesh=region_mesh, uv_set=uv_set,
            ))
            positions[name] = _reflect_x(pos) if side == target_side else pos

    for side in (source_side, target_side):
        side_parent = group_name
        flip = None
        if side == target_side:
            flip = f'corrective_{side}_flip'
            if not cmds.objExists(flip):
                cmds.group(empty=True, world=True, name=flip)
                result.created.append(flip)
            _parent_preserve_world(flip, group_name)
            side_parent = flip
            if flip not in result.flip_groups:
                result.flip_groups.append(flip)

        root = f'ChestCorRoot_{side}_guide'
        # Match the clavicle position, staged before the corrective flip.
        clav = f'clav_{side}_guide'
        if not cmds.objExists(clav):
            raise RuntimeError(f'Missing chest corrective root anchor: {clav}')
        root_position = _position(clav)
        if side == target_side:
            root_position = _reflect_x(root_position)
        if not cmds.objExists(root):
            info = create_guide_from_position(
                pos=root_position,
                guide_name=f'ChestCorRoot_{side}',
                parent=None,
            )
            if info.name != root:
                raise RuntimeError(f'Unexpected corrective root: {info.name}')
            result.created.append(root)
        else:
            result.existing.append(root)
        _parent_preserve_world(root, side_parent)
        # Workshop's medium guide display (joint drawStyle 3).
        if cmds.nodeType(root) == 'joint':
            cmds.setAttr(f'{root}.radius', cfg.get('root_radius', 2.5))
            cmds.setAttr(f'{root}.drawStyle', 3)

        for part in parts:
            name = f'{part}_{side}_guide'
            if not cmds.objExists(name):
                info = create_guide_from_position(
                    pos=positions[name], guide_name=f'{part}_{side}', parent=None,
                )
                if info.name != name:
                    raise RuntimeError(f'Unexpected corrective guide: {info.name}')
                result.created.append(name)
            else:
                result.existing.append(name)
            _parent_preserve_world(name, root)

        # Each corrective family owns a separate insert and orientation.
        corrective_sets = (
            ('pec_insert', ('pec_01', 'pec_02')),
            ('trap_insert', ('trap_01', 'trap_02')),
            ('necktrap_insert', ('necktrap_01',)),
        )
        for insert_part, child_parts in corrective_sets:
            insert = f'{insert_part}_{side}_guide'
            children = [f'{part}_{side}_guide' for part in child_parts]
            if cfg.get('orient', True):
                orient_ik_correctives(insert, children)
            else:
                for child in children:
                    _parent_preserve_world(child, insert)

        if flip:
            cmds.setAttr(f'{flip}.scaleX', -1.0)


def build_character_guides(
    config: str | Path | dict | None = None,
    mesh: str | None = None,
    uv_set: str | None = None,
    *,
    allow_reference_fallback: bool = False,
    dry_run: bool = False,
    orient: bool = True,
    refresh_every: int = 5,
    symmetry: dict | None = None,
) -> GuideBuildResult:
    """Build a first-pass guide hierarchy from a JSON config.

    Run in an empty guide scene. Existing guide nodes are reused, not replaced.
    dry_run validates placement without creating guides.
    """
    config = _load_config(DEFAULT_CONFIG if config is None else config)
    # Optional facial entries join the SAME build; no separate face builder.
    config = dict(config)
    config['guides'] = list(config.get('guides', []))
    config['orientation_groups'] = list(config.get('orientation_groups', []))
    face_cfg = config.get('face_guides', {})
    if face_cfg.get('enabled', False):
        for entry in face_cfg.get('guides', []):
            item = dict(entry)
            item['placement'] = dict(entry['placement'])
            item['placement'].setdefault('layer', 'face')
            config['guides'].append(item)
        config['orientation_groups'].extend(face_cfg.get('orientation_groups', []))
    _validate_config(config)
    mesh = mesh or config['mesh']
    uv_set = uv_set or config.get('uv_set', 'PG_Guides')
    result = GuideBuildResult()
    symmetry = symmetry if symmetry is not None else config.get('symmetry', {})
    direction = symmetry.get('direction', 'L_to_R')
    if direction not in ('L_to_R', 'R_to_L'):
        raise ValueError('symmetry.direction must be L_to_R or R_to_L')
    source_side, target_side = direction.split('_to_')
    mirrored_categories = {
        cat for cat in ('arms', 'legs', 'face') if _mirror_enabled(cat, symmetry)
    }

    if not cmds.objExists(mesh):
        raise RuntimeError(f'Mesh does not exist: {mesh}')

    skipped = {
        _guide_name(e['name']) for e in config.get('guides', [])
        if _side(_guide_name(e['name'])) == target_side
        and _category(_guide_name(e['name'])) in mirrored_categories
    }
    positions = _resolve_positions(
        config, mesh, uv_set,
        allow_reference_fallback=allow_reference_fallback,
        result=result,
        skip_regions=skipped,
    )
    for name in skipped:
        source_name = name.replace(f'_{target_side}_', f'_{source_side}_')
        if source_name in positions:
            positions[name] = _reflect_x(positions[source_name])
    _resolve_match_parent_positions(config, positions)

    # Head medium guides are procedural, not solved from body polygroups.
    head_cfg = config.get('head_placement', {})
    head_positions = {}
    if head_cfg.get('enabled', False):
        root_name = head_cfg.get('root', 'head_root_M_guide')
        end_name = head_cfg.get('end', 'head_ee_M_guide')
        if root_name not in positions or end_name not in positions:
            raise RuntimeError('Head placement requires resolved head root and head end')
        head_positions = head_guide_positions(
            positions[root_name], positions[end_name],
            start=head_cfg.get('start', 0.1),
            stop=head_cfg.get('stop', 0.5),
            forward_fraction=head_cfg.get('forward_fraction', 0.1),
        )
        positions.update(head_positions)

    # Compute the desired final positions first. Symmetric destinations
    # derive from the source; asymmetric destinations keep their own regions.
    # ALL target-side guides are staged on the opposite side of the X-scale flip
    # group, then flipped exactly once after parenting/orientation.
    for entry in config.get('guides', []):
        name = _guide_name(entry['name'])
        if _side(name) != target_side:
            continue
        category = _category(name)
        if category not in ('arms', 'legs', 'face'):
            continue
        if category in mirrored_categories:
            source_name = name.replace(f'_{target_side}_', f'_{source_side}_')
            if source_name not in positions:
                raise RuntimeError(f'Missing symmetry source: {source_name}')
            desired = _reflect_x(positions[source_name])
        else:
            desired = positions[name]
        positions[name] = _reflect_x(desired)

    # Resolve compound spline endpoint positions from their declared anchors.
    spline_positions = []
    for spline in config.get('splines', []):
        anchors = []
        for key in ('lower_placement', 'upper_placement'):
            placement = spline[key]
            method = placement['method']
            if method == 'match_parent':
                parent = placement['parent']
                if parent in positions:
                    anchors.append(positions[parent])
                elif cmds.objExists(parent):
                    anchors.append(_position(parent))
                else:
                    raise RuntimeError(f"Missing spline anchor {parent!r} for {spline['name']}")
            elif method == 'region':
                region = placement['region']
                try:
                    pos = solve_position(
                        GuidePlacement(name=key, region=region),
                        mesh=mesh, uv_set=uv_set,
                    )
                    anchors.append(tuple(pos))
                except (LookupError, KeyError, ValueError, RuntimeError) as exc:
                    result.missing_regions.append(f"{spline['name']} {key}: {region} ({exc})")
                    if allow_reference_fallback and 'reference_position' in placement:
                        anchors.append(tuple(placement['reference_position']))
                    else:
                        raise RuntimeError(f"Cannot resolve spline anchor {region!r}") from exc
            else:
                raise ValueError(f"Unsupported spline placement method: {method}")
        spline_positions.append((spline, anchors[0], anchors[1]))

    # Foot-roll landmarks: same symmetry decision as the legs. The target
    # side is always staged in its leg flip group's unflipped coordinates.
    foot_roll_positions = {}
    foot_cfg = config.get('foot_roll', {})
    if foot_cfg.get('enabled', False):
        for side in ('L', 'R'):
            region_side = source_side if (
                side == target_side and 'legs' in mirrored_categories
            ) else side
            landmarks = {}
            for key in ('heel', 'toeball_ground', 'bankout', 'bankin'):
                region = foot_cfg['regions'][key].format(side=region_side)
                try:
                    pos = tuple(solve_position(
                        GuidePlacement(name=f'{key}_{region_side}', region=region),
                        mesh=mesh, uv_set=uv_set,
                    ))
                except (LookupError, KeyError, ValueError, RuntimeError) as exc:
                    result.missing_regions.append(f'foot_roll {side}: {region} ({exc})')
                    fallback = foot_cfg.get('reference_positions', {}).get(region_side, {}).get(key)
                    if not allow_reference_fallback or fallback is None:
                        raise RuntimeError(f'Cannot resolve foot-roll region {region!r}') from exc
                    pos = tuple(fallback)
                if side == target_side and 'legs' not in mirrored_categories:
                    pos = _reflect_x(pos)
                landmarks[key] = pos
            foot_roll_positions[side] = landmarks

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
    step_count = 0

    def refresh_progress(message: str) -> None:
        nonlocal step_count
        step_count += 1
        if refresh_every > 0 and step_count % refresh_every == 0:
            print(f'[Workshop] {message}')
            cmds.refresh(force=True)

    try:
        for entry in config.get('guides', []):
            name = _guide_name(entry['name'])
            if cmds.objExists(name):
                result.existing.append(name)
                refresh_progress(f"Reusing {name}")
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
            refresh_progress(f"Created {name}")

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
            cmds.refresh(force=True)

        # Orient independent chains before final parenting.
        if orient:
            for group in config.get('orientation_groups', []):
                chain = group['chain']
                if not all(cmds.objExists(node) for node in chain):
                    result.warnings.append(f"Skipped orientation: {group['name']} (missing guide)")
                    continue
                if group.get('force_planar', False):
                    try:
                        force_planar_guides(
                            guides=group.get('planar_chain', chain),
                            keep_endpoints=group.get('keep_endpoints', False),
                        )
                    except ValueError as exc:
                        result.warnings.append(f"Planar solve skipped for {group['name']}: {exc}")
                orient_limb_guides(
                    guides=chain,
                    aim_axis=group.get('aim_axis', 'y'),
                    up_axis=group.get('up_axis', 'z'),
                )
                refresh_progress(f"Oriented {group['name']}")

        # Body uses category flip groups. Face uses one flip group per
        # non-target-side parent, so nose/ears/cheeks remain organized
        # beneath their actual anatomical parent guides.
        flip_groups = {}
        for category in ('arms', 'legs'):
            parent = {'arms': 'chest_root_M_guide', 'legs': 'cog_M_guide'}[category]
            group = _make_flip_group(category, target_side, parent)
            flip_groups[category] = group
            result.flip_groups.append(group)

        face_flip_groups = {}

        # Parent regular guides in dependency order. For splines, their
        # endpoint guides are handled below; tangent parents stay as built.
        pending = {}
        for entry in config.get('guides', []):
            child = _guide_name(entry['name'])
            parent = entry['parent']
            cat = _category(child)

            if _side(child) == target_side and cat == 'face':
                # Keep target-side descendants under their own guides.
                # A flip group is needed only where a target-side
                # facial branch attaches to a non-target-side parent.
                if _side(parent) != target_side or _category(parent) != 'face':
                    if parent not in face_flip_groups:
                        stem = parent.removesuffix('_guide')
                        group_name = f'{stem}_{target_side}_flip'
                        if cmds.objExists(group_name):
                            raise RuntimeError(
                                f'Flip group already exists: {group_name}; '
                                'use a clean guide scene'
                            )
                        group = cmds.group(
                            empty=True, world=True, name=group_name
                        )
                        # Parent without inheriting an offset transform:
                        # these groups must remain at the origin until flipped.
                        _parent_preserve_world(group, parent)
                        face_flip_groups[parent] = group
                        result.flip_groups.append(group)
                    parent = face_flip_groups[parent]

            elif _side(child) == target_side and cat in flip_groups:
                if _side(parent) != target_side or _category(parent) != cat:
                    parent = flip_groups[cat]

            pending[child] = parent
        while pending:
            progressed = False
            for child, parent in list(pending.items()):
                if parent not in pending and cmds.objExists(parent):
                    _parent_preserve_world(child, parent)
                    refresh_progress(f"Parented {child}")
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
            # Cluster-deformed spline curves must stay directly under guides
            # to avoid inheriting parent motion a second time.
            curve = _guide_name(f"{spline.get('curve_name', spline['name'])}_{side}")
            if cmds.objExists(curve):
                _parent_curve_guide(curve, 'guides')
                _style_curve_guide(curve)

        # Foot-roll guides inherit the leg flip hierarchy automatically.
        # Build after legs/toes are parented, but before scaleX is flipped.
        for side, landmarks in foot_roll_positions.items():
            created_roll = build_foot_roll_guides(
                side=side,
                heel_position=landmarks['heel'],
                toeball_position=landmarks['toeball_ground'],
                bankout_position=landmarks['bankout'],
                bankin_position=landmarks['bankin'],
            )
            result.created.extend(created_roll.values())
            refresh_progress(f'Built foot roll {side}')

        # Flip each target-side component once, after every child is parented.
        for group in (*flip_groups.values(), *face_flip_groups.values()):
            cmds.setAttr(f'{group}.scaleX', -1.0)
            cmds.refresh(force=True)

        # Explicit styling pass: keep large and medium head guides visible
        # with the established Workshop radius/drawStyle convention.
        for item in config.get('big_guides', []):
            _set_big_guide(_guide_name(item), radius=5.0)

        if head_positions:
            style_head_guides(
                head_positions,
                radius=head_cfg.get('radius', 2.5),
            )

        _build_chest_corrective_guides(config, mesh, result, symmetry)
        _build_curve_guides(config, mesh, result)
        _build_eyeball_guides(config, result)

        cmds.refresh(force=True)
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
