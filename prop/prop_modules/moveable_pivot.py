from attr import dataclass
import maya.cmds as cmds

from Workshop.control.core import create_control, Control
from Workshop.tag.core import lock_tag
from Workshop.transform.utils import create_transform
from Workshop.maya_api.node import MultiplyDivideNode



@dataclass
class module_info:
    pivot_offset:Control
    pivot_control:Control
    pivot_driven:str
    pivot_inverse:str


def moveable_pivot(transform:str, name_overwite:str|None, control_size:float=1, parent:str|None = None, rig_type:str=''):
    base_name = name_overwite if name_overwite else transform
    pivot_offset = create_control(name=f'{base_name}_pivot_offset', transform=transform, control_shape='circle', parent=parent, size=control_size, color_type=rig_type)
    lock_tag(object=pivot_offset.ctrl, translate=(False, False, False), rotate=(True,True,True), scale=(True,True,True), visibility=True, hide_tag=True)
    pivot = create_control(name=f'{base_name}_pivot', transform=transform, control_shape='sphere', parent=pivot_offset.ctrl, size=control_size/2, color_type=rig_type)
    lock_tag(object=pivot.ctrl, translate=(False, False, False), rotate=(False, False, False), scale=(True,True,True), visibility=True, hide_tag=True)

    object_parent = cmds.listRelatives(transform, parent=True)[0]
    if not object_parent:
        print(f'parent missing on {transform}')
    pivot_driven = create_transform(name=f'{base_name}_pivot_driven', transform=transform, parent=object_parent)
    lock_tag(pivot_driven)
    pivot_inverse = create_transform(name=f'{base_name}_pivot_inverse', transform=transform, parent=pivot_driven)

    inverse = MultiplyDivideNode(name=f'{base_name}')
    inverse.input1.connect_from(f'{pivot_offset.ctrl}.translate')
    inverse.input2.set((-1,-1,-1))
    inverse.output.connect_to(f'{pivot_inverse}.translate')

    cmds.parentConstraint(pivot.ctrl, pivot_driven, maintainOffset=True)
    cmds.parent(transform, pivot_inverse)
    return module_info(pivot_offset=pivot_offset, pivot_driven = pivot_driven, pivot_control=pivot, pivot_inverse=pivot_inverse)





