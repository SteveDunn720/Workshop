import maya.cmds as mc


def bake_scale_pivot_into_translate(objects=None):

    if not objects:
        objects = mc.ls(sl=True, type="transform") or []

    if not objects:
        print("No objects selected")
        return

    for obj in objects:

        if not mc.objExists(obj):
            continue

        print(f"\n--- Processing {obj} ---")

        # -----------------------------
        # 1. GET WORLD SCALE PIVOT
        # -----------------------------
        pivot = mc.xform(obj, q=True, ws=True, scalePivot=True)

        print("Original world pivot:", pivot)

        # -----------------------------
        # 2. GET TRANSLATE
        # -----------------------------
        t = mc.getAttr(obj + ".translate")[0]

        # -----------------------------
        # 3. BIAS TRANSLATE BY -PIVOT
        # (bake pivot into translate)
        # -----------------------------
        new_translate = [
            t[0] - pivot[0],
            t[1] - pivot[1],
            t[2] - pivot[2]
        ]

        mc.setAttr(obj + ".translate", *new_translate)

        print("New translate:", new_translate)

        # -----------------------------
        # 4. FREEZE TRANSFORMS (ONLY TRANSLATE)
        # -----------------------------
        mc.makeIdentity(obj, apply=True, translate=True, rotate=False, scale=False, normal=False)

        # -----------------------------
        # 5. RESTORE PIVOT (WORLD SPACE)
        # -----------------------------
        current = mc.getAttr(obj + ".translate")[0]
        
        new_translate = [
            current[0] + pivot[0],
            current[1] + pivot[1],
            current[2] + pivot[2]
        ]
        
        mc.setAttr(obj + ".translate", *new_translate)

        print(f"Done: {obj}")
bake_scale_pivot_into_translate()



import maya.cmds as cmds


def cleanup_uv_sets(uv_name="map1"):
    selection = cmds.ls(sl=True, long=True)

    if not selection:
        cmds.warning("Nothing selected.")
        return

    for obj in selection:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []

        for shape in shapes:
            if cmds.nodeType(shape) != "mesh":
                continue

            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []

            if not uv_sets:
                continue

            primary_uv = uv_sets[0]

            # Rename the first UV set if needed
            if primary_uv != uv_name:
                try:
                    cmds.polyUVSet(
                        shape,
                        rename=True,
                        uvSet=primary_uv,
                        newUVSet=uv_name
                    )
                except:
                    cmds.warning(f"Could not rename UV set on {shape}")

            # Refresh list after rename
            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []

            # Delete all extra UV sets
            for uv in uv_sets:
                if uv != uv_name:
                    try:
                        cmds.polyUVSet(
                            shape,
                            delete=True,
                            uvSet=uv
                        )
                    except:
                        cmds.warning(f"Could not delete {uv} on {shape}")

    print("UV cleanup complete.")


cleanup_uv_sets("map1")



import maya.cmds as cmds
from collections import defaultdict

def find_duplicate_dag_names():
    # Get all DAG nodes as full paths
    all_nodes = cmds.ls(dag=True, long=True) or []

    name_map = defaultdict(list)

    # Group by short name
    for node in all_nodes:
        short_name = node.split("|")[-1]
        name_map[short_name].append(node)

    # Find duplicates
    duplicates_found = False

    for name, nodes in sorted(name_map.items()):
        if len(nodes) > 1:
            duplicates_found = True
            print(f"\nDUPLICATE NAME: {name}")
            for n in nodes:
                print(f"  - {n}")

    if not duplicates_found:
        print("No duplicate DAG node names found.")

find_duplicate_dag_names()




import sys
modules = [name for name in sys.modules.keys() if name.startswith("Workshop")]
for name in modules:
    del sys.modules[name]
import Workshop

 
  
from Workshop.meta_rigs.build import build

build()



from Workshop.meta_rigs.meta_componets.ik import generate_autoPV
generate_autoPV(['thigh_l', 'calf_l', 'foot_l'], 'your_mom')
generate_autoPV(['upperarm_l', 'lowerarm_l', 'hand_l'], 'your_mom2')



from Workshop.UE_asset_export.auto_lod_export import export_verified_asset


export_verified_asset('DoorA')


from Workshop.UE_asset_export.UI_exporter import show_ui
show_ui()


    del sys.modules[name]
import yrig

from yrig.blendshape import read_blendshape, write_blendshape



write_blendshape(
    blendshape_node='test_shape',
    shape_path= r'/users/student/s/sd547/Documents/Maya/projects/default/assets/test.shp',
)

read_blendshape(
    target_mesh='body_geo',
    blendshape_name='test_shape',
    shape_path= r'/users/student/s/sd547/Documents/Maya/projects/default/assets/test.shp',)
        
              

import maya.cmds as cmds

def straighten_uvs_scale():
    sel = cmds.ls(sl=True, fl=True)

    if not sel:
        cmds.warning("Select edges or UVs.")
        return

    # Detect selection type
    if ".e[" in sel[0]:
        # Convert edges → UVs
        uvs = cmds.polyListComponentConversion(sel, toUV=True)
        uvs = cmds.ls(uvs, fl=True)
    elif ".map[" in sel[0]:
        uvs = sel
    else:
        cmds.warning("Please select edges or UVs.")
        return

    if not uvs:
        cmds.warning("No UVs found.")
        return

    # Deduplicate
    uvs = list(set(uvs))

    # Select UVs (important for polyEditUV scaling)
    cmds.select(uvs)

    # Get positions
    u_vals = []
    v_vals = []

    uv_pos = {}

    for uv in uvs:
        u, v = cmds.polyEditUV(uv, q=True)
        uv_pos[uv] = (u, v)
        u_vals.append(u)
        v_vals.append(v)

    # Compute ranges
    u_range = max(u_vals) - min(u_vals)
    v_range = max(v_vals) - min(v_vals)

    # Compute pivot (center)
    pivot_u = sum(u_vals) / len(u_vals)
    pivot_v = sum(v_vals) / len(v_vals)

    # Decide axis and scale
    if u_range > v_range:
        # Horizontal → flatten V
        cmds.polyEditUV(pu=pivot_u, pv=pivot_v, su=1, sv=0)
    else:
        # Vertical → flatten U
        cmds.polyEditUV(pu=pivot_u, pv=pivot_v, su=0, sv=1)

    print("UVs straightened via scaling.")

straighten_uvs_scale()


import sys
modules = [name for name in sys.modules.keys() if name.startswith("rjg")]
for name in modules:
    del sys.modules[name]
import rjg


# Run to import yrig and its components
import sys
import os
from pathlib import Path
dev_path = Path("/users/student/s/sd547/Desktop/New Repo/y-rig/").expanduser() # Replace with the path to your y-rig repo
yrig_path = (dev_path / Path("src")).resolve()
venv_path = (dev_path / Path(".venv/lib/python3.11/site-packages")).resolve()
if str(yrig_path) not in sys.path:
    sys.path.insert(0, str(yrig_path))
if str(venv_path) not in sys.path:
    sys.path.insert(0, str(venv_path))
import yrig
component_path = (dev_path / Path("shifter/components")).resolve()
os.environ["MGEAR_SHIFTER_COMPONENT_PATH"] = str(component_path)

import sys
modules = [name for name in sys.modules.keys() if name.startswith("yrig")]
for name in modules:
    del sys.modules[name]
import yrig

import dcc.maya.rig.builder
dcc.maya.rig.builder.ui.launch()

# Run to open debug port
import os
from pathlib import Path
import debugpy
maya_path = Path(os.environ.get("MAYA_LOCATION")) # type:ignore
mayapy_path = (maya_path / Path("bin/mayapy")).resolve()
debugpy.configure({'python': str(mayapy_path)})
debugpy.listen(5678) # 5678 is the default attach port in the VS Code debug configurations. Host defaults to 127.0.0.1


#/users/student/s/sd547/Desktop/New Repo/y-rig




# Run to reload yrig during development
import sys
modules = [name for name in sys.modules.keys() if name.startswith("yrig")]
for name in modules:
    del sys.modules[name]
import yrig

mc.delete('eye_L')
mc.delete('eye_R')

from yrig.component.y_eye_01.eye import Eye

eye_L = Eye(
    part="eye",
    side="L",
    parent="face_grp",
    control_parent="neck_M0_head_ctl",
    control_size=1,
)

eye_L.build()

eye_R = Eye(
    part="eye",
    side="R",
    parent="face_grp",
    control_parent="neck_M0_head_ctl",
    control_size=1,
)

eye_R.build()



from yrig.control import create_control
main_ctrl = create_control(
            name='test',
            parent=None,
            transform='null1',
            size=1,
            control_shape="round_square",
            direction="z",
            position_offset=(10,10,10),
        )
