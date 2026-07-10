from Workshop.prop import prop_modules
from Workshop.control.core import create_control
from Workshop.joint import create_joint

import maya.cmds as cmds

from Workshop.tag.core import get_tags


def build_simple_melee_prop(guides:list, rig_name:str):
    prop_rig_root = prop_modules.configure_prop_scene()

    rig_root:str = prop_rig_root.rig 
    rig_size:float = prop_rig_root.scene_size

    root = prop_modules.Root(control_size=rig_size, parent=rig_root)
    root_info = root.root_build()

    chain = prop_modules.pivot_chain(guides=[guides[0], guides[2]], name_overwrites=['tip', 'bot'],  controls=True, control_size=rig_size/4, rig_type='pivots')
    cmds.parent(chain.top, root_info.offset_control.ctrl)

    main_control = create_control(name='main', transform=guides[1], control_shape='circle', parent=chain.controls[-1].ctrl, size=rig_size/2, color_type='main')
    main_joint = create_joint(name='main', transform=main_control.ctrl, parent=root_info.root_joint)

    moveable = prop_modules.moveable_pivot(transform=chain.controls[0].ctrl, name_overwite='main', control_size=rig_size/3, rig_type='pivots', parent=root_info.offset_control.ctrl)




    # check for and apply tags

    rig_nodes = cmds.listRelatives(rig_root, allDescendents=True, fullPath=False, shapes=False, type="transform")

    for node in rig_nodes:
        get_tags(node)