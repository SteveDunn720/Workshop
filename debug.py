import maya.cmds as cmds

def debug_tweaks(label: str, geo_root: str = "geo"):

    shapes = cmds.listRelatives(
        geo_root,
        allDescendents=True,
        type="mesh",
        fullPath=True,
    ) or []

    tweaks = set()

    for shape in shapes:
        history = cmds.listHistory(shape) or []

        for node in history:
            if cmds.nodeType(node) == "tweak":
                tweaks.add(node)

    print(f"\n--- {label} ---")

    if not tweaks:
        print("NO TWEAKS")
        return

    for tweak in sorted(tweaks):
        print("TWEAK:", tweak)