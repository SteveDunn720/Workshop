from attr import dataclass

import maya.cmds as cmds

from Workshop.transform.utils import create_transform
from Workshop.control.core import Control
from Workshop.transform.utils import create_space_switch
from Workshop.tag.core import obj_vis_tag


@dataclass
class module:
    main_grp:str
    control_grp:str
    guts:str
    fk_grp:str
    ik_grp:str

def module_prep(part: str, side: str, parent: str, fkik:bool=False, gut:bool=True)->module:
    main_grp = create_transform(name=f"{part}_{side}", parent=parent)
    control_grp = create_transform(name=f"{part}_CTRLS_{side}", parent=main_grp)
    if gut:
        guts = create_transform(name=f"{part}_GUTS_{side}", parent=main_grp)
        obj_vis_tag(guts, 'ALWAYS')
    else:
        guts = ''
    if fkik:
        ik_control_grp = create_transform(name=f"{part}_IK_controls_{side}", parent=control_grp)
        fk_control_grp = create_transform(name=f"{part}_Fk_controls_{side}", parent=control_grp)
    else:
        ik_control_grp = ''
        fk_control_grp = ''

    prep = module(main_grp=main_grp, control_grp=control_grp, guts=guts, fk_grp=fk_control_grp, ik_grp=ik_control_grp)
    
    return prep

def module_space(space_list:list, control:Control):
    if len(space_list) == 0:
        pass
    elif len(space_list) == 1:
        cmds.parentConstraint(space_list[0], control.top, maintainOffset=True)
    else:
        create_space_switch(target_transform=control.top, parents=space_list, target_control=control.ctrl)