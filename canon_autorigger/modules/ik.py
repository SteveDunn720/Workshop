from attr import dataclass
import maya.cmds as cmds
from Workshop.transform.utils import create_transform, match_location, get_distance_between, get_plane_normal, get_position, convert_to_matrix
from Workshop.control.core import Control
from Workshop.maya_api.node import MultiplyDivideNode, SumNode
from Workshop.transform.constraint import constraint, Constraint


@dataclass
class IK_data:
    start_joint:str
    end_joint:str
    handle:str
    effector:str
    spline_curve:str
    type:str
    pole_vector:str

@dataclass
class AutoPvData:
    top:str
    offset:str
    driver:str
    space_constraint:Constraint
    twist_attr:str


def create_IK_rotate_plane(name:str, start_joint:str, end_joint:str, mid_joint:str, pole_vector_guide:str, auto_pv:bool=False, mirror_pv:bool=False)->IK_data:
    ik_handle, effector = cmds.ikHandle(                                                 #type:ignore
            name=f'{name}_IK_handle',
            startJoint=start_joint,
            endEffector=end_joint,
            solver="ikRPsolver"
        )

    if auto_pv:
        pv = generate_autoPV([start_joint, mid_joint, end_joint], f'{name}_PV', mirror=mirror_pv)
    else:
        pv = pole_vector_guide

    pv_loc = cmds.spaceLocator(name=f'{name}_pv_loc')[0]
    match_location(pv_loc, pv) #type:ignore
    if mirror_pv:
        cmds.setAttr(f'{pv_loc}.scaleX', -1)

    if auto_pv:
        cmds.delete(pv)
    
    cmds.poleVectorConstraint(pv_loc, ik_handle)#type:ignore                                              
    
    handle = IK_data(start_joint=start_joint, end_joint=end_joint, handle=ik_handle, effector=effector, spline_curve='', type='rotate_plane', pole_vector=pv_loc)       
    
    return handle                                                   

    

def generate_autoPV(joints: list, name: str = "pv_name", mirror:bool=False) -> str:

    p0 = get_position(joints[0])
    p1 = get_position(joints[1])
    p2 = get_position(joints[2])

    limb_dir = (p2 - p0)
    limb_dir.normalize()

    normal = get_plane_normal(joints[0], joints[1], joints[2])
    normal.normalize()

    # stable PV direction (THIS is the fix)
    pv_dir = normal ^ limb_dir
    pv_dir.normalize()

    # distance scale
    first_dist = (p1 - p0).length()
    second_dist = (p2 - p1).length()
    avg_dist = (first_dist + second_dist) * -1

    mid_pos = p1

    pv_pos = mid_pos + (pv_dir * avg_dist)

    pv_matrix = convert_to_matrix(pos=(pv_pos.x, pv_pos.y, pv_pos.z))

    pv_object = create_transform(name=name, parent=None, transform=pv_matrix)
    if mirror:
            cmds.setAttr(f'{pv_object}.scaleX', -1) #type:ignore

    return pv_object

def auto_pv_space(end_control:Control, pv_control:Control, parent:str, parent_space:str, ignore_end_orient:bool=False) -> AutoPvData:
    top = create_transform(name=f'{pv_control.name}_auto_pv_top', parent=parent, transform=end_control.ctrl)
    if ignore_end_orient:
        for axis in ['X', 'Y', 'Z']:
            cmds.setAttr(f'{top}.rotate{axis}')
    cmds.addAttr(pv_control.ctrl, longName='auto_pv_twist_mult', maxValue=1, minValue=0, defaultValue=.5, keyable=True)
    twist_attr=f'{pv_control.ctrl}.auto_pv_twist_mult'

    space_constraint = constraint(drivers=[parent_space], driven=top, parent=parent)

    offset = create_transform(name=f'{pv_control.name}_auto_pv_offset', parent=top, transform=top)
    driver = create_transform(name=f'{pv_control.name}_auto_pv_driver', parent=offset, transform=top)

    for attr in ['translate', 'rotate',]:
        for axis in ['X', 'Y', 'Z']:
            cmds.connectAttr(f'{end_control.ctrl}.{attr}{axis}', f'{offset}.{attr}{axis}') # probably need a more fool proof set up here, but this works for now
    

    mult = MultiplyDivideNode(name=f'{pv_control.name}_auto_pv_mult')
    sum = SumNode(name=f'{pv_control.name}_auto_pv_sumY')

    sum.output.connect_to(f"{driver}.translateY")

    mult.input1.x.connect_from(f'{end_control.ctrl}.translateZ')
    mult.input2.x.set(-1)
    mult.output.x.connect_to(sum.input[0])

    sum.input[1].connect_from(f'{end_control.ctrl}.rotateX')

    mult.input1.y.connect_from(f'{end_control.ctrl}.translateZ')
    mult.input2.y.set(-.75)
    mult.output.z.connect_to(f"{driver}.translateZ")

    mult.input1.z.connect_from(f'{end_control.ctrl}.rotateY')
    mult.input2.z.connect_from(twist_attr)
    mult.output.z.connect_to(f"{driver}.rotateY")


    info = AutoPvData(top=top, offset=offset, driver=driver, space_constraint=space_constraint, twist_attr=twist_attr)

    return info
    

def create_IK_single_chain(name:str, start_joint:str, end_joint:str,)->IK_data:
    ik_handle, effector = cmds.ikHandle(                                                 #type:ignore
            name=f'{name}_IK_handle',
            startJoint=start_joint,
            endEffector=end_joint,
            solver="ikSCsolver"
        )                            
    
    handle = IK_data(start_joint=start_joint, end_joint=end_joint, handle=ik_handle, effector=effector, spline_curve='', type='single_chain', pole_vector='')       
    
    return handle  
