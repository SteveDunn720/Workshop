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

        # Establish unscaled flip groups at world origin. All guides on
        # target side (mirrored OR independently solved) use these groups.
        flip_groups = {}
        for category in ('arms', 'legs', 'face'):
            if category == 'face' and not face_cfg.get('enabled', False):
                continue
            parent = {'arms': 'chest_root_M_guide', 'legs': 'cog_M_guide', 'face': 'head_root_M_guide'}[category]
            group = _make_flip_group(category, target_side, parent)
            flip_groups[category] = group
            result.flip_groups.append(group)

        # Parent regular guides in dependency order. For splines, their
        # endpoint guides are handled below; tangent parents stay as built.
        pending = {}
        for entry in config.get('guides', []):
            child = _guide_name(entry['name'])
            parent = entry['parent']
            cat = _category(child)
            if _side(child) == target_side and cat in flip_groups:
                # Replace the first cross-category/root parent with flip group.
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
            # Curve itself stays under the guides root, independent of endpoint parents.
            curve = _guide_name(f"{spline.get('curve_name', spline['name'])}_{side}")
            if cmds.objExists(curve):
                _parent_preserve_world(curve, 'guides')

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
        for group in flip_groups.values():
            cmds.setAttr(f'{group}.scaleX', -1.0)
            cmds.refresh(force=True)

        for item in config.get('big_guides', []):
            _set_big_guide(_guide_name(item), radius=5.0)
        if head_positions:
            style_head_guides(head_positions, radius=head_cfg.get('radius', 2.5))

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
