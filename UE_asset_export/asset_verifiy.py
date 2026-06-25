from dataclasses import dataclass, field
import re
import maya.cmds as cmds



@dataclass
class AssetInfo:
    asset_name: str

    lod_count: int = 0

    lods: list[int] = field(default_factory=list)

    sub_assets: list[str] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)


def get_children(node):
    return cmds.listRelatives(
        node,
        children=True,
        type="transform"
    ) or []


def extract_lod(name):
    match = re.search(r"_lod_(\d+)", name)
    return int(match.group(1)) if match else None


def strip_lod(name):
    return re.sub(r"_lod_\d+$", "", name)


def verify_asset(asset_name):

    result = AssetInfo(asset_name)

    root = f"{asset_name}_grp"

    if not cmds.objExists(root):
        result.errors.append(
            f"Missing root group: {root}"
        )
        return result

    lod_groups = {}

    # ------------------------
    # Find LOD groups
    # ------------------------

    for child in get_children(root):

        lod = extract_lod(child)

        if lod is None:
            result.errors.append(
                f"Invalid child under root: {child}"
            )
            continue

        if not child.endswith("_grp"):
            result.errors.append(
                f"LOD group missing _grp suffix: {child}"
            )

        lod_groups[lod] = child

    if not lod_groups:
        result.errors.append("No LOD groups found.")
        return result

    result.lods = sorted(lod_groups.keys())

    # ------------------------
    # LOD numbering checks
    # ------------------------

    if 0 not in lod_groups:
        result.errors.append(
            "LODs must begin at lod_0."
        )

    max_lod = max(lod_groups)

    for i in range(max_lod + 1):
        if i not in lod_groups:
            result.errors.append(
                f"Missing lod_{i}_grp."
            )

    result.lod_count = max_lod + 1

    # ------------------------
    # Build canonical list from lod_0
    # ------------------------

    canonical = set()

    if 0 in lod_groups:

        for child in get_children(lod_groups[0]):

            lod = extract_lod(child)

            if lod != 0:
                result.errors.append(
                    f"{child} is inside lod_0_grp but named lod_{lod}"
                )

            base = strip_lod(child)

            canonical.add(base)

        result.sub_assets = sorted(canonical)

    # ------------------------
    # Validate all other LODs
    # ------------------------

    for lod_num, lod_group in lod_groups.items():

        current_assets = set()

        for child in get_children(lod_group):

            child_lod = extract_lod(child)

            # Wrong numbering
            if child_lod != lod_num:
                result.errors.append(
                    f"{child} is inside lod_{lod_num}_grp "
                    f"but named lod_{child_lod}"
                )

            # Naming convention
            expected_suffix = f"_lod_{lod_num}"

            if not child.endswith(expected_suffix):
                result.errors.append(
                    f"{child} has invalid naming."
                )

            base = strip_lod(child)
            current_assets.add(base)

        # Compare against lod_0
        if lod_num != 0:

            missing = canonical - current_assets
            extra = current_assets - canonical

            for asset in sorted(missing):
                result.warnings.append(
                    f"LOD {lod_num} missing {asset}"
                )

            for asset in sorted(extra):
                result.warnings.append(
                    f"LOD {lod_num} contains unexpected asset {asset}"
                )

    return result