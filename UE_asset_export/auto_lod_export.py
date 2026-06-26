import os
import maya.cmds as cmds
from Workshop.UE_asset_export.asset_verifiy import verify_asset, extract_lod
from Workshop.UE_asset_export.asset_handeling import restore_layout, return_to_origin
from Workshop.UE_asset_export.asset_manifest_export import write_manifest





EXPORT_ROOT = r"C:/Users/sd547/Box/Sprint2026/Mistborn/test_repo"


def export_verified_asset(asset_name: str, ignore_warnings: bool = False, export_root: str = EXPORT_ROOT):
    """
    Full pipeline:
    - verify asset (LOD system)
    - optionally block on warnings
    - build export directory
    - export each sub-asset as OBJ
    - preserve layout transforms safely
    """

    # -------------------------
    # 1. VERIFY
    # -------------------------
    result = verify_asset(asset_name)

    if result.errors:
        print("❌ EXPORT ABORTED — ERRORS FOUND:")
        for e in result.errors:
            print("  ", e)
        return

    if result.warnings and not ignore_warnings:
        print("⚠️ EXPORT ABORTED — WARNINGS FOUND:")
        for w in result.warnings:
            print("  ", w)
        print("\nSet ignore_warnings=True to override.")
        return

    root = f"{asset_name}_grp"

    if not cmds.objExists(root):
        print(f"Root missing: {root}")
        return

    # -------------------------
    # 2. BUILD DIRECTORY STRUCTURE
    # -------------------------
    asset_export_dir = os.path.join(export_root, asset_name)
    os.makedirs(asset_export_dir, exist_ok=True)

    lod_groups = {}

    for child in cmds.listRelatives(root, children=True, type="transform") or []:
        lod = extract_lod(child)
        if lod is not None:
            lod_groups[lod] = child

    
    write_manifest(asset_name=asset_name, export_root=export_root, filename=f'{asset_name}_manifest')
    # -------------------------
    # 3. EXPORT EACH LOD + SUB-ASSET
    # -------------------------
    for lod, lod_group in sorted(lod_groups.items()):

        lod_dir = os.path.join(asset_export_dir, f"lod_{lod}")
        os.makedirs(lod_dir, exist_ok=True)

        sub_assets = cmds.listRelatives(lod_group, children=True, type="transform") or []

        for sub in sub_assets:

            # skip non-geo transforms if needed
            shapes = cmds.listRelatives(sub, shapes=True) or []
            if not shapes:
                continue

            # -----------------------------------
            # A. store + zero transform
            # -----------------------------------
            return_to_origin(sub)

            # -----------------------------------
            # B. export OBJ
            # -----------------------------------
            export_path = os.path.join(lod_dir, f"{sub}.obj")

            cmds.select(sub, r=True)

            cmds.file(
                export_path,
                force=True,
                options="groups=0;ptgroups=0;materials=0;smoothing=1;normals=1",
                type="OBJexport",
                exportSelected=True
            )

            print(f"Exported: {sub} → {export_path}")

            # -----------------------------------
            # C. restore layout
            # -----------------------------------
            restore_layout(sub)