import json
import os
import maya.cmds as cmds
from Workshop.UE_asset_export.asset_verifiy import verify_asset, strip_lod


def write_manifest(
        asset_name: str,
        export_root: str,
        filename: str = "manifest.json"):
    """
    Generates an asset manifest describing
    all LODs and sub-assets.
    """

    result = verify_asset(asset_name)

    if result.errors:
        raise RuntimeError(
            f"Asset {asset_name} failed verification:\n"
            + "\n".join(result.errors)
        )

    root = f"{asset_name}_grp"

    manifest = {
        "asset_name": asset_name,
        "lod_count": result.lod_count,
        "sub_assets": result.sub_assets,
        "lods": {}
    }

    for lod in result.lods:

        lod_group = f"{asset_name}_lod_{lod}_grp"

        if not cmds.objExists(lod_group):
            continue

        manifest["lods"][str(lod)] = {}

        children = cmds.listRelatives(
            lod_group,
            children=True,
            type="transform"
        ) or []

        for child in children:

            base_name = strip_lod(child)

            relative_path = os.path.join(
                f"lod_{lod}",
                f"{child}.obj"
            )

            manifest["lods"][str(lod)][base_name] = relative_path

    asset_dir = os.path.join(export_root, asset_name)
    os.makedirs(asset_dir, exist_ok=True)

    manifest_path = os.path.join(asset_dir, filename)

    with open(manifest_path, "w") as f:
        json.dump(
            manifest,
            f,
            indent=4
        )

    print(f"Manifest written: {manifest_path}")

    return manifest_path