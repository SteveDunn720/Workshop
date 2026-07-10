from attr import dataclass

from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.transform.utils import create_transform



@dataclass
class module_info:
    top:str
    controls:list
    transforms:list
    joints:list


def pivot_chain(guides:list[str], name_overwrites:list[str] | None,  controls:bool=True, joints:bool=False, control_size:float=1, rig_type:str='')->module_info:
    parent=None
    jnt_parent =None
    ctrls = []
    jnts = []
    tforms = []
    for i, guide in enumerate(guides):
        name = guide if not name_overwrites else name_overwrites[i]
        if controls and not joints:
            control = create_control(name=name, transform=guide, control_shape='cube', parent=parent, size=control_size, color_type=rig_type)
            parent= control.ctrl
            ctrls.append(control)
            
        elif joints and not controls:
            joint = create_joint(name=f'{name}',transform=guide,connect=False, parent=parent)
            parent=joint
            jnts.append(joint)
        elif joints and controls:
            control = create_control(name=name, transform=guide, control_shape='cube', parent=parent, size=control_size, color_type=rig_type)
            joint = create_joint(name=f'{name}',transform=control.ctrl,connect=True, parent=jnt_parent)
            parent= control.ctrl
            jnt_parent=joint
            ctrls.append(control)
            jnts.append(joint)
        else:
            tform = create_transform(name=name, parent=parent, transform=guide)
            parent=tform
            tforms.append(tform)
    if controls:
        top=ctrls[0].top
    elif joints and not controls:
        top=jnts[0]
    else:
        top=tforms[0]
    return module_info(top=top, controls=ctrls, transforms=tforms, joints=jnts)
        



    